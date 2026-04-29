import json
import os
from pathlib import Path

from dotenv import load_dotenv
from backend.mistral_client import get_mistral_client, chat_complete_with_retry


env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

client = get_mistral_client()

SOURCE_HINTS = [
    {
        "keywords": ["sbi", "state bank of india"],
        "sources": [
            {"label": "State Bank of India", "url": "https://sbi.co.in/"},
        ],
    },
    {
        "keywords": ["hdfc"],
        "sources": [
            {"label": "HDFC Bank", "url": "https://www.hdfcbank.com/"},
        ],
    },
    {
        "keywords": ["idfc"],
        "sources": [
            {"label": "IDFC FIRST Bank", "url": "https://www.idfcfirstbank.com/"},
        ],
    },
    {
        "keywords": ["axis"],
        "sources": [
            {"label": "Axis Bank", "url": "https://www.axisbank.com/"},
        ],
    },
    {
        "keywords": ["bank of baroda", "baroda"],
        "sources": [
            {"label": "Bank of Baroda", "url": "https://www.bankofbaroda.in/"},
        ],
    },
    {
        "keywords": ["rbi", "remittance", "forex", "lrs", "fema", "bank"],
        "sources": [
            {"label": "Reserve Bank of India", "url": "https://www.rbi.org.in/"},
            {"label": "RBI Foreign Exchange FAQs", "url": "https://www.rbi.org.in/commonperson/English/Scripts/FAQs.aspx?Id=1834"},
        ],
    },
    {
        "keywords": ["tax", "tds", "tcs", "itr", "income tax"],
        "sources": [
            {"label": "Income Tax Department", "url": "https://www.incometax.gov.in/iec/foportal/"},
        ],
    },
    {
        "keywords": ["stock", "trading", "investment", "sebi"],
        "sources": [
            {"label": "SEBI", "url": "https://www.sebi.gov.in/"},
        ],
    },
    {
        "keywords": ["fraud", "scam", "phishing", "cyber"],
        "sources": [
            {"label": "RBI Customer Awareness", "url": "https://www.rbi.org.in/commonperson/english/Scripts/Notification.aspx"},
            {"label": "National Cyber Crime Portal", "url": "https://cybercrime.gov.in/"},
        ],
    },
]


def infer_sources(question: str):
    q = question.lower()
    matched = []
    seen = set()
    for group in SOURCE_HINTS:
        if any(keyword in q for keyword in group["keywords"]):
            for source in group["sources"]:
                key = source["url"]
                if key not in seen:
                    seen.add(key)
                    matched.append(source)
    return matched


def build_local_answer(question: str):
    q = question.lower()

    if any(keyword in q for keyword in ["what is ai", "define ai", "artificial intelligence", "machine learning", "ml", "what is machine learning"]):
        return {
            "answer": (
                "Artificial intelligence is the field of building computer systems that can perform tasks that normally "
                "require human intelligence, such as understanding language, recognizing patterns, making predictions, "
                "and supporting decisions. Machine learning is a subset of AI where models learn patterns from data "
                "instead of relying only on hard-coded rules."
            ),
            "key_points": [
                "AI is an umbrella term for systems that mimic cognitive tasks like reasoning and pattern recognition.",
                "Machine learning learns from historical data and improves performance on similar tasks over time.",
                "In finance, AI is commonly used for fraud detection, risk scoring, forecasting, and compliance monitoring.",
            ],
        }

    if any(keyword in q for keyword in ["remittance", "forex", "lrs", "fema", "abroad", "foreign transfer"]):
        return {
            "answer": (
                "Delayed or undeclared foreign remittances can trigger additional scrutiny from the bank because "
                "RBI and FEMA reporting rules expect the purpose, remitter details, and supporting documents to be "
                "accurate at the time of transfer. If the amount is high, the bank may also apply enhanced due "
                "diligence and tax-related checks before processing or regularizing the transfer."
            ),
            "key_points": [
                "Confirm the exact purpose code and declaration details with the authorized dealer bank.",
                "Keep KYC, source-of-funds, beneficiary, and invoice or education documents ready.",
                "Ask the bank whether the transfer needs correction, re-reporting, or additional FEMA documentation.",
            ],
        }

    if any(keyword in q for keyword in ["fraud", "scam", "phishing", "suspicious transaction", "unauthorized"]):
        return {
            "answer": (
                "A suspicious banking transaction should be treated as urgent because the bank's response window and "
                "your liability can depend on how quickly you report it. Fast reporting helps freeze channels, "
                "preserve evidence, and improve the chance of limiting losses."
            ),
            "key_points": [
                "Report the transaction to the bank immediately and block cards, UPI, or net banking if needed.",
                "Keep screenshots, SMS alerts, account statements, and call details as evidence.",
                "File a cybercrime or fraud complaint if the transaction appears unauthorized.",
            ],
        }

    if any(keyword in q for keyword in ["rbi", "sebi", "tax", "tds", "tcs", "compliance"]):
        return {
            "answer": (
                "The answer depends on the exact transaction type, amount, and whether the activity was properly "
                "declared or reported. In finance and compliance questions, the safest next step is usually to match "
                "the scenario to the governing regulator, then confirm thresholds, forms, and timelines from the "
                "official source."
            ),
            "key_points": [
                "Identify whether the issue is banking, remittance, tax, lending, or securities related.",
                "Check the amount threshold because many reporting duties start only above specific limits.",
                "Verify the rule against the official regulator or institution before acting.",
            ],
        }

    return {
        "answer": (
            "Here is a practical baseline view based on common Indian finance and compliance guidance. "
            "To make this fully scenario-specific, include the exact transaction type, amount, timeline, and "
            "what was already declared or reported. With those details, the response can be narrowed to the "
            "right compliance path and likely next actions."
        ),
        "key_points": [
            "Include the amount, product type, and whether the action was declared or reported.",
            "Mention the regulator or bank if the question is tied to a specific institution.",
            "Use the official source links below to validate limits and procedures.",
        ],
    }


def sanitize_plain_text(value: str):
    text = str(value)
    # Normalize common mojibake and keep text UI-friendly.
    text = text.replace("â€™", "'").replace("â€“", "-").replace("â€œ", '"').replace("â€\x9d", '"')
    text = " ".join(text.split())
    return text


def sanitize_payload(payload: dict):
    if not isinstance(payload, dict):
        return payload
    if "answer" in payload:
        payload["answer"] = sanitize_plain_text(payload["answer"])
    if isinstance(payload.get("key_points"), list):
        payload["key_points"] = [sanitize_plain_text(point) for point in payload["key_points"]]
    return payload


def normalize_fallback_response(payload: dict, question: str, inferred_sources: list[dict]):
    if not isinstance(payload, dict):
        payload = {}

    answer = payload.get("answer") or build_local_answer(question)["answer"]
    key_points = payload.get("key_points") if isinstance(payload.get("key_points"), list) else []

    normalized = {
        "answer": sanitize_plain_text(answer),
        "key_points": [sanitize_plain_text(point) for point in key_points[:5]],
        "sources": payload.get("sources") or inferred_sources,
        "helpful_links": payload.get("helpful_links") or inferred_sources,
        "source_reliability": payload.get("source_reliability") or {
            "score": 0.7,
            "label": "MEDIUM",
            "reason": "Fallback response used. Validate against official regulator links before taking action.",
        },
        "mode": payload.get("mode", "FALLBACK"),
        "rule_matches": payload.get("rule_matches", []),
        "rules_checked": payload.get("rules_checked", 0),
        "rule_summary": payload.get("rule_summary", "Lightweight AI fallback used."),
    }

    return sanitize_payload(normalized)


def ask_agent_fallback(question: str, history: str = ""):
    prompt = f"""
You are FinTrix, a practical fintech assistant.

Conversation:
{history}

Question:
{question}

Return strict JSON only with this exact structure:
{{
  "answer": "A detailed but readable explanation in 4 to 6 sentences.",
  "key_points": [
    "Short actionable point",
    "Short actionable point"
  ],
  "sources": [],
  "helpful_links": [],
  "mode": "FALLBACK",
  "rule_matches": [],
  "rules_checked": 0,
  "rule_summary": "Lightweight AI fallback used."
}}

Rules:
- Make the answer useful for a real user, not a developer.
- Explain the concept briefly, then mention a practical caution or next step.
- Keep key_points concise and actionable.
- Do not return markdown.
"""

    inferred_sources = infer_sources(question)

    try:
        response = chat_complete_with_retry(
            client,
            model="grok-4.20",
            messages=[{"role": "user", "content": prompt}],
            attempts=2,
            base_delay=0.5,
        )
        content = (
            response.choices[0].message.content.strip()
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(content[start:end])
            return normalize_fallback_response(parsed, question, inferred_sources)
    except Exception:
        pass

    local_answer = build_local_answer(question)

    return normalize_fallback_response({
        "answer": local_answer["answer"],
        "key_points": local_answer["key_points"],
        "mode": "FALLBACK",
    }, question, inferred_sources)
