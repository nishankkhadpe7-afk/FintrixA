"""
LLM-based rule extractor for regulator content.

Sends raw content to Gemini API and returns structured rule JSON.
Output is treated as UNTRUSTED — validation happens downstream.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, conlist, field_validator

logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path, override=False)


def _read_env_value(key: str) -> str:
    try:
        with open(dotenv_path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.getenv(key, "").strip()


GEMINI_API_KEY = _read_env_value("GEMINI_API_KEY")
MISTRAL_API_KEY = _read_env_value("MISTRAL_API_KEY")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
ENABLE_MISTRAL_FALLBACK = os.getenv("ENABLE_MISTRAL_FALLBACK", "true").lower() == "true"
USE_VERTEX_AI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"
GOOGLE_CLOUD_PROJECT = _read_env_value("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = _read_env_value("GOOGLE_CLOUD_LOCATION") or "global"

TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds
MAX_CHUNK_CHARS = 7000
CHUNK_OVERLAP_CHARS = 600
SEBI_MAX_RETRIES = 3
SEBI_RETRY_DELAY = 4
SEBI_MAX_CHUNK_CHARS = 5000
SEBI_CHUNK_OVERLAP_CHARS = 450

BASE_EXTRACTION_PROMPT = """You are a financial regulatory rule compiler for {source}.

Your task is to extract ONLY strict, executable rules from the provided regulatory text.

OBJECTIVE:
Convert the text into machine-executable JSON rules for a deterministic rule engine.

VALID RULE REQUIREMENTS:
Extract a rule ONLY if ALL are present:
1. FIELD
2. OPERATOR
3. VALUE
4. ACTION
If any is missing, ignore that candidate.

ALLOWED OPERATORS:
equals, not_equals, greater_than, less_than, greater_than_or_equal, less_than_or_equal, in, not_in, exists, contains

ALLOWED ACTION RESULTS:
allow, deny, flag, require

STRICT INSTRUCTIONS:
- Extract ONLY explicit rules
- DO NOT guess or infer
- DO NOT convert vague statements into rules
- DO NOT extract descriptive, explanatory, introductory, definitional, interpretive, or boilerplate text
- Preserve exact thresholds and categories
- Use snake_case field names
- Prefer precision over recall
- Return at most 15 rules for this chunk

IGNORE COMPLETELY:
- introductions
- summaries
- explanations
- examples
- definitions
- notes
- repeated boilerplate
- legal references without executable conditions

PIPELINE-COMPATIBLE OUTPUT FORMAT:
Return ONLY valid JSON with this exact structure:
{{{{
  "rules": [
    {{{{
      "type": "eligibility | restriction | obligation | exception",
      "title": "short title",
      "conditions": [
        {{{{
          "field": "snake_case_field_name",
          "operator": "equals | not_equals | greater_than | less_than | greater_than_or_equal | less_than_or_equal | in | not_in | exists | contains",
          "value": "number | string | boolean | list"
        }}}}
      ],
      "logic": "AND | OR",
      "action": {{{{
        "result": "allow | deny | flag | require",
        "message": "clear explanation of the rule"
      }}}},
      "metadata": {{{{
        "source": "{source}",
        "confidence": 0.0,
        "section": "exact clause / section reference if available",
        "text_snippet": "exact supporting sentence from the document"
      }}}}
    }}}}
  ]
}}}}

HARD CONSTRAINTS:
- If no valid executable rules exist, return {{"rules": []}}
- Each rule must have at least one explicit condition
- Each rule must have a concrete value
- Each rule must have a clear action
- If a chunk has no executable rule, return an empty rules array

QUALITY CHECK:
Before outputting a rule, verify:
- the condition is explicit
- the value is concrete
- the action is clear
If any check fails, discard the rule.

Return ONLY JSON. No markdown. No prose.

TEXT CHUNK {chunk_number}/{chunk_total}:
{content}
"""

RBI_EXTRACTION_APPENDIX = """

RBI-SPECIFIC GUIDANCE:
- Focus on prudential norms, exposure rules, borrower eligibility, lending restrictions, KYC, and remittance controls.
- Normalize terms like borrower type, lender type, tenor, collateral, and exposure thresholds when they are explicitly stated.
- Prefer executable thresholds, category checks, and approval/review triggers.
- Skip policy background and narrative explanation text.
"""

SEBI_EXTRACTION_APPENDIX = """

SEBI-SPECIFIC GUIDANCE:
- Focus on disclosure obligations, market access restrictions, investor eligibility, intermediary compliance, trading controls, and listing conditions.
- Preserve references to chapters, regulations, schedules, circular numbers, and clause identifiers when available.
- Prefer 2-8 HIGH-CONFIDENCE executable rules per chunk, not exhaustive clause dumping.
- Skip definitions, interpretation text, background explanations, forms, annexure labels, document templates, and procedural boilerplate unless they create an actual compliance decision.
- Only return rules that can be executed with at least one concrete condition and a clear compliance outcome.
- If a chunk contains no executable rule, return {"rules": []}.
- Prefer explicit disclosure thresholds, filing deadlines, eligibility gates, prohibition conditions, and approval/review triggers.
"""


class ExtractedCondition(BaseModel):
    field: str
    operator: str
    value: Any


class ExtractedAction(BaseModel):
    result: str
    message: str


class ExtractedMetadata(BaseModel):
    source: str
    confidence: float = 1.0
    section: str = ""

    @field_validator("confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"\d+(?:\.\d+)?", value)
            if match:
                return float(match.group(0))
            return 1.0
        return 1.0


class ExtractedRule(BaseModel):
    type: str
    title: str
    conditions: conlist(ExtractedCondition, min_length=1)
    logic: str = "AND"
    action: ExtractedAction
    metadata: ExtractedMetadata


def extract_rules_from_content(content: str, url: str = "", source: str = "RBI") -> List[Dict[str, Any]]:
    """
    Extract structured rules from raw circular content via LLM.

    Args:
        content: Raw circular text
        url: Source URL (for logging)

    Returns:
        List of rule dictionaries (UNTRUSTED — needs downstream validation)
    """
    if TEST_MODE:
        logger.info(f"TEST MODE: returning mock rules for {url}")
        return _mock_rules(url, source=source)

    has_gemini_provider = (USE_VERTEX_AI and bool(GOOGLE_CLOUD_PROJECT)) or bool(GEMINI_API_KEY)
    if not has_gemini_provider and not (ENABLE_MISTRAL_FALLBACK and MISTRAL_API_KEY):
        logger.error("No LLM provider configured. Set Vertex AI project/location or GEMINI_API_KEY, or enable Mistral fallback.")
        return []

    chunks = _chunk_content(content, source=source)
    all_rules: List[Dict[str, Any]] = []
    seen_signatures = set()

    for index, chunk in enumerate(chunks, start=1):
        prompt = _build_prompt(
            source=source,
            chunk_number=index,
            chunk_total=len(chunks),
            content=chunk,
        )
        rules = _extract_rules_for_prompt(
            prompt,
            url=url,
            chunk_number=index,
            chunk_total=len(chunks),
            source=source,
        )
        for rule in rules:
            signature = json.dumps(rule, sort_keys=True, default=str)
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                all_rules.append(rule)

    all_rules = _post_filter_rules(all_rules, source=source)

    logger.info(f"LLM extracted {len(all_rules)} total rules from {url} across {len(chunks)} chunk(s)")
    return all_rules


def _build_prompt(source: str, chunk_number: int, chunk_total: int, content: str) -> str:
    appendix = RBI_EXTRACTION_APPENDIX if source.upper() == "RBI" else SEBI_EXTRACTION_APPENDIX if source.upper() == "SEBI" else ""
    return (
        BASE_EXTRACTION_PROMPT + appendix
    ).format(
        source=source,
        chunk_number=chunk_number,
        chunk_total=chunk_total,
        content=content,
    )


def _chunk_content(content: str, source: str = "RBI") -> List[str]:
    text = content.strip()
    max_chunk_chars = SEBI_MAX_CHUNK_CHARS if source.upper() == "SEBI" else MAX_CHUNK_CHARS
    overlap_chars = SEBI_CHUNK_OVERLAP_CHARS if source.upper() == "SEBI" else CHUNK_OVERLAP_CHARS

    if len(text) <= max_chunk_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    step = max_chunk_chars - overlap_chars

    while start < len(text):
        end = min(start + max_chunk_chars, len(text))
        if end < len(text):
            split_window = text[start:end]
            candidate = max(
                split_window.rfind("\n\n"),
                split_window.rfind(". "),
                split_window.rfind("\n"),
            )
            if candidate > max_chunk_chars // 2:
                end = start + candidate + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap_chars, start + step)

    return chunks


def _extract_rules_for_prompt(
    prompt: str,
    url: str,
    chunk_number: int,
    chunk_total: int,
    source: str = "RBI",
) -> List[Dict[str, Any]]:
    max_retries = SEBI_MAX_RETRIES if source.upper() == "SEBI" else MAX_RETRIES
    retry_delay = SEBI_RETRY_DELAY if source.upper() == "SEBI" else RETRY_DELAY

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "LLM extraction attempt %s/%s for %s chunk %s/%s",
                attempt,
                max_retries,
                url,
                chunk_number,
                chunk_total,
            )

            raw_content = _generate_llm_text(
                prompt=prompt,
                timeout=90 if source.upper() == "SEBI" else 60,
            )
            rules = _parse_llm_output(raw_content)
            if rules is not None:
                return rules

        except Exception as e:
            logger.warning(f"LLM extraction attempt {attempt} failed: {e}")

        if attempt < max_retries:
            delay = retry_delay * (2 ** (attempt - 1))
            time.sleep(delay)

    logger.error(f"LLM extraction failed after {max_retries} attempts for {url} chunk {chunk_number}/{chunk_total}")
    return []


def _generate_llm_text(prompt: str, timeout: int) -> str:
    provider_errors: List[str] = []

    if GEMINI_API_KEY:
        try:
            return _generate_with_gemini(prompt)
        except Exception as exc:
            provider_errors.append(f"Gemini: {exc}")
            logger.warning("Gemini generation failed: %s", exc)

    if ENABLE_MISTRAL_FALLBACK and MISTRAL_API_KEY:
        try:
            return _generate_with_mistral(prompt, timeout=timeout)
        except Exception as exc:
            provider_errors.append(f"Mistral fallback: {exc}")
            logger.warning("Mistral fallback generation failed: %s", exc)

    raise RuntimeError("; ".join(provider_errors) or "No LLM provider available")


def _generate_with_gemini(prompt: str) -> str:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai SDK is not installed") from exc

    client_kwargs: Dict[str, Any]
    if USE_VERTEX_AI:
        if not GOOGLE_CLOUD_PROJECT:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Vertex AI mode")
        client_kwargs = {
            "vertexai": True,
            "project": GOOGLE_CLOUD_PROJECT,
            "location": GOOGLE_CLOUD_LOCATION,
        }
    else:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini Developer API mode")
        client_kwargs = {"api_key": GEMINI_API_KEY}

    client = genai.Client(**client_kwargs)
    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=prompt,
        config={
            "temperature": 0.0,
            "top_p": 1.0,
            "max_output_tokens": 1500,
        },
    )

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text


def _generate_with_mistral(prompt: str, timeout: int) -> str:
    response = httpx.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "mistral-small",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        },
        timeout=timeout,
    )

    data = response.json()
    if "choices" not in data:
        raise RuntimeError(f"Mistral returned no choices: {data}")
    return data["choices"][0]["message"]["content"]


def _post_filter_rules(rules: List[Dict[str, Any]], source: str = "RBI") -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for rule in rules:
        title = str(rule.get("title", "")).strip().lower()
        conditions = rule.get("conditions") or []
        action = ((rule.get("action") or {}).get("result") or "").strip().lower()

        if not conditions:
            continue
        if action not in {"allow", "deny", "require", "flag"}:
            continue
        if source.upper() == "SEBI":
            if any(keyword in title for keyword in {"definition", "interpretation", "applicability", "form", "annexure"}):
                continue
        filtered.append(rule)
    return filtered


def _parse_llm_output(content: str) -> Optional[List[Dict[str, Any]]]:
    """Parse LLM response into JSON. Handles markdown wrappers."""
    try:
        # Strip markdown code block if present
        if content.strip().startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)

        # Handle both {"rules": [...]} and [...] formats
        if isinstance(parsed, dict) and "rules" in parsed:
            return _validate_extracted_rules(parsed["rules"])
        elif isinstance(parsed, list):
            return _validate_extracted_rules(parsed)
        else:
            logger.warning(f"Unexpected LLM output format: {type(parsed)}")
            return None

    except json.JSONDecodeError as e:
        logger.warning(f"LLM output is not valid JSON: {e}")
        return None


def _validate_extracted_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    validated = []
    for item in rules:
        try:
            model = ExtractedRule.model_validate(item)
            validated.append(model.model_dump())
        except ValidationError as exc:
            logger.warning("Skipping invalid extracted rule: %s", exc)
            continue
    return validated


def _mock_rules(url: str, source: str = "RBI") -> List[Dict[str, Any]]:
    """Mock rules for testing without API calls."""
    return [
        {
            "type": "eligibility",
            "title": "State borrowing commission exclusion",
            "conditions": [
                {"field": "borrower_type", "operator": "equals", "value": "state_government"},
                {"field": "lender_type", "operator": "equals", "value": "cooperative_bank"},
            ],
            "logic": "AND",
            "action": {
                "result": "deny",
                "message": "Not eligible for agency commission",
            },
            "metadata": {
                "source": source,
                "confidence": 0.95,
                "section": "Mock rule for testing",
            },
        },
        {
            "type": "restriction",
            "title": "Long term borrowing restriction",
            "conditions": [
                {"field": "loan_term", "operator": "equals", "value": "long_term"},
                {"field": "borrower_type", "operator": "equals", "value": "state_government"},
            ],
            "logic": "AND",
            "action": {
                "result": "flag",
                "message": "Long term state government borrowings require additional review",
            },
            "metadata": {
                "source": source,
                "confidence": 0.9,
                "section": "Mock rule for testing",
            },
        },
    ]
