import json
import os
from dotenv import load_dotenv

# Load .env from the script's directory
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path, override=True)

def _read_env_value(key: str) -> str:
    try:
        with open(dotenv_path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.getenv(key, "").strip()


API_KEY = _read_env_value("GEMINI_API_KEY")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
USE_VERTEX_AI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"
GOOGLE_CLOUD_PROJECT = _read_env_value("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = _read_env_value("GOOGLE_CLOUD_LOCATION") or "global"

def extract_rules(text: str):
    # 🧪 TEST MODE - return mock rules for testing
    if TEST_MODE:
        return [
            {
                "type": "eligibility",
                "title": "Exclusion of Short Term/Long Term Borrowings from Agency Commission",
                "conditions": [
                    {
                        "field": "borrower_type",
                        "operator": "==",
                        "value": "State Government"
                    },
                    {
                        "field": "source_of_funds",
                        "operator": "in",
                        "value": ["financial institutions", "banks"]
                    }
                ],
                "action": "not_eligible_for_agency_commission"
            }
        ]

    if USE_VERTEX_AI and not GOOGLE_CLOUD_PROJECT:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set for Vertex AI mode")
    if not USE_VERTEX_AI and not API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    prompt = f"""
You are a financial compliance rule extractor.

Extract ONLY deterministic rules.

Return JSON array of rules with:
- type (eligibility, prohibition, conditional, aggregation)
- title
- conditions (field, operator, value)
- action

STRICT:
- Output ONLY valid JSON
- No explanation text

TEXT:
{text}
"""

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai SDK is not installed") from exc

    client_kwargs = {
        "vertexai": True,
        "project": GOOGLE_CLOUD_PROJECT,
        "location": GOOGLE_CLOUD_LOCATION,
    } if USE_VERTEX_AI else {"api_key": API_KEY}

    client = genai.Client(**client_kwargs)
    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=prompt,
        config={
            "temperature": 0.0,
            "top_p": 1.0,
            "max_output_tokens": 1500
        }
    )

    content = getattr(response, "text", "") or ""
    if not content:
        print("❌ LLM ERROR: empty Gemini response")
        return []

    try:
        # Remove markdown code block if present
        if content.startswith("```"):
            # Extract JSON from ```json ... ``` wrapper
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]  # Remove "json" prefix
            content = content.strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"LLM parsing failed: {e}")
        print(content)
        return []
