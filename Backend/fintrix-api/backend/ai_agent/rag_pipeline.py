import numpy as np
from backend.ai_agent.vector_store import load_vector_store
from backend.mistral_client import get_mistral_client
from backend.mistral_client import chat_complete_with_retry
from rank_bm25 import BM25Okapi
import os
from dotenv import load_dotenv
import json
import re
from pathlib import Path
from backend.ai_agent.topic_guard import (
    build_off_topic_response,
    build_welcome_response,
    classify_question_scope,
)
import logging

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("MISTRAL_API_KEY")
ALLOW_REMOTE_MODEL_DOWNLOAD = os.getenv("FINTRIX_AI_ALLOW_REMOTE_DOWNLOAD", "0") == "1"

client = get_mistral_client()
model = None
model_load_error = None

SOURCE_MAP = {
    "axis.pdf": "axis.pdf",
    "BANK OF BARODA.pdf": "bank_of_baroda.pdf",
    "FEEDRAL BANK.pdf": "feedral.pdf",
    "HDFC Bank.pdf": "hdfc.pdf",
    "IDFC FIRST Bank.pdf": "idfc.pdf",
    "RBI.pdf": "RBI.pdf",
    "sbi.pdf": "sbi.pdf"
}

LINK_MAP = {
    "rbi": [
        {"title": "RBI Guidelines", "url": "https://www.rbi.org.in"}
    ],
    "hdfc": [
        {"title": "HDFC Forex Services", "url": "https://www.hdfcbank.com/personal/money-transfer/foreign-exchange"}
    ],
    "idfc": [
        {"title": "IDFC FIRST Bank", "url": "https://www.idfcfirstbank.com/"}
    ],
    "icici": [
        {"title": "ICICI Forex Guide", "url": "https://www.icicibank.com/forex"}
    ],
    "sbi": [
        {"title": "SBI Forex", "url": "https://sbi.co.in"}
    ],
    "sebi": [
        {"title": "SEBI Official Website", "url": "https://www.sebi.gov.in/"}
    ],
    "axis": [
        {"title": "Axis Forex", "url": "https://www.axisbank.com"}
    ],
    "bank_of_baroda": [
        {"title": "Bank of Baroda", "url": "https://www.bankofbaroda.in/"}
    ],
    "federal": [
        {"title": "Federal Bank", "url": "https://www.federalbank.co.in/"}
    ],
    "education": [
        {"title": "RBI LRS Scheme", "url": "https://www.rbi.org.in"}
    ],
    "default": [
        {"title": "RBI Official Website", "url": "https://www.rbi.org.in"}
    ]
}

TRUSTED_DOCS = {
    "axis.pdf",
    "bank_of_baroda.pdf",
    "feedral.pdf",
    "hdfc.pdf",
    "idfc.pdf",
    "RBI.pdf",
    "sbi.pdf",
}

SOURCE_GROUPS = {
    "rbi": {"RBI.pdf"},
    "axis": {"axis.pdf"},
    "hdfc": {"HDFC Bank.pdf"},
    "idfc": {"IDFC FIRST Bank.pdf"},
    "bank_of_baroda": {"BANK OF BARODA.pdf"},
    "federal": {"FEEDRAL BANK.pdf"},
    "sbi": {"sbi.pdf"},
    "sebi": set(),
}


def get_embedding_model():
    global model, model_load_error

    if model is not None:
        return model

    if model_load_error is not None:
        return None

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            local_files_only=not ALLOW_REMOTE_MODEL_DOWNLOAD,
        )
        return model
    except Exception as exc:
        mode = "local cache only" if not ALLOW_REMOTE_MODEL_DOWNLOAD else "remote download allowed"
        model_load_error = f"Embedding model unavailable ({mode}): {exc}"
        return None


def detect_source_intent(question: str):
    q = question.lower()
    matches = []
    if "sebi" in q:
        matches.append("sebi")
    if "rbi" in q or "lrs" in q or "fema" in q or "remittance" in q:
        matches.append("rbi")
    if "axis" in q:
        matches.append("axis")
    if "hdfc" in q:
        matches.append("hdfc")
    if "idfc" in q:
        matches.append("idfc")
    if "bank of baroda" in q or "baroda" in q:
        matches.append("bank_of_baroda")
    if "federal" in q:
        matches.append("federal")
    if re.search(r"\bsbi\b", q):
        matches.append("sbi")
    return matches

def allowed_sources_for_question(question: str):
    intents = detect_source_intent(question)
    allowed = set()
    for intent in intents:
        allowed.update(SOURCE_GROUPS.get(intent, set()))
    return intents, allowed


def helpful_links_for_question(question: str, sources):
    q = question.lower()
    detected_intents = detect_source_intent(question)
    source_names = {str(item.get("file", "")).lower() for item in sources}

    if "sebi" in detected_intents:
        return LINK_MAP["sebi"]
    if "rbi" in detected_intents or any("rbi" in source for source in source_names):
        return LINK_MAP["rbi"]
    if "hdfc" in detected_intents:
        return LINK_MAP["hdfc"]
    if "idfc" in detected_intents or any("idfc" in source for source in source_names):
        return LINK_MAP["idfc"]
    if "bank_of_baroda" in detected_intents or any("baroda" in source or "bank_of_baroda" in source for source in source_names):
        return LINK_MAP["bank_of_baroda"]
    if "federal" in detected_intents or any("feedral" in source or "federal" in source for source in source_names):
        return LINK_MAP["federal"]
    if "axis" in detected_intents:
        return LINK_MAP["axis"]
    if "sbi" in detected_intents:
        return LINK_MAP["sbi"]
    if "icici" in q:
        return LINK_MAP["icici"]
    if "education" in q or "study" in q:
        return LINK_MAP["education"]
    return LINK_MAP["default"]

def detect_mode(question: str):
    q = question.lower()

    if any(w in q for w in ["how", "steps", "guide", "help", "process"]):
        return "GUIDE"

    if any(w in q for w in ["what if", "risk", "penalty", "illegal","consequence", "can i", "is it allowed","will i get caught", "problem if"]):
        return "INLINE_WHATIF"

    if any(w in q for w in ["scenario", "case", "suppose", "if i do"]):
        return "REDIRECT"

    return "EXPLAIN"

def detect_depth(question: str):
    q = question.lower()

    if len(q.split()) <= 3:
        return "SHORT"

    if any(w in q for w in ["what", "define", "meaning"]):
        return "SHORT"

    if any(w in q for w in ["list", "types", "points"]):
        return "POINTS"

    return "DETAILED"


def normalize_answer_text(text: str):
    # Keep answers concise, clean, and easy to scan.
    if not isinstance(text, str):
        text = str(text)
    text = " ".join(text.split())
    text = text.replace("\n", " ")

    # Split into sentences and keep a short readable answer.
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if len(parts) > 4:
        parts = parts[:4]
    return " ".join(parts)


def normalize_key_points(points):
    if not isinstance(points, list):
        return []
    cleaned = []
    for point in points:
        p = " ".join(str(point).split())
        p = p.strip("-•* ")
        if p:
            cleaned.append(p)
    return cleaned[:6]


def source_reliability_summary(sources):
    if not sources:
        return {
            "score": 0.35,
            "label": "LOW",
            "reason": "No retrievable citations were attached.",
        }

    trusted = 0
    for item in sources:
        file_name = str(item.get("file", ""))
        if file_name in TRUSTED_DOCS:
            trusted += 1

    score = 0.55 + (0.15 * trusted)
    score = min(score, 0.95)

    if score >= 0.85:
        label = "HIGH"
        reason = "Answer is grounded in curated institutional PDFs from the FinTrix knowledge base."
    elif score >= 0.7:
        label = "MEDIUM"
        reason = "Answer is partially grounded in curated sources; verify critical thresholds before action."
    else:
        label = "LOW"
        reason = "Limited trusted citations were found for this response."

    return {"score": round(score, 2), "label": label, "reason": reason}

def ask_agent(question, history=""):
    question = question.strip()
    scope = classify_question_scope(question)

    if scope == "greeting":
        return build_welcome_response()

    if scope == "off_topic":
        return build_off_topic_response()

    embedding_model = get_embedding_model()
    mode = detect_mode(question)
    response_style = detect_depth(question)
    if "previous" in question.lower() or "above" in question.lower() or "that" in question.lower():
        mode = "GUIDE"
    index, texts, metadata, tokenized_texts = load_vector_store()

    bm25 = BM25Okapi(tokenized_texts)
    tokenized_query = question.lower().split()
    detected_intents, allowed_sources = allowed_sources_for_question(question)
    strict_source_mode = bool(detected_intents)

    bm25_scores = bm25.get_scores(tokenized_query)
    bm25_top_idx = np.argsort(bm25_scores)[-3:][::-1]

    vector_distances = []
    combined_indices = list(bm25_top_idx)

    if embedding_model is not None:
        query_embedding = embedding_model.encode([question])
        distances, indices = index.search(np.array(query_embedding), k=5)
        vector_distances = list(distances[0])
        combined_indices = list(indices[0]) + combined_indices

    combined_indices = list(dict.fromkeys(combined_indices))

    if strict_source_mode:
        if allowed_sources:
            combined_indices = [
                idx for idx in combined_indices
                if metadata[idx].get("source") in allowed_sources
            ]
        else:
            combined_indices = []
    
    context_chunks = []

    # If not in strict source mode, use top vector results as base if they are relevant enough
    if not strict_source_mode and (not vector_distances or vector_distances[0] > 1.3):
        context_chunks.extend(combined_indices[:3])

    # Add chunks that have keyword matches
    for i in combined_indices:
        chunk = texts[i]
        if sum(word in chunk.lower() for word in tokenized_query) >= 1:
            context_chunks.append(i)

    # Fallback if no chunks selected
    if not context_chunks and not strict_source_mode:
        context_chunks = combined_indices[:3]

    # Deduplicate and limit to 3 best chunks
    seen_idx = set()
    final_chunks = []
    for idx in context_chunks:
        if idx not in seen_idx:
            final_chunks.append(idx)
            seen_idx.add(idx)
    
    context_chunks = final_chunks[:3]
    

    context = ""
    history = "\n".join(history.split("\n")[-6:])

    for i in context_chunks:
        chunk = texts[i]
        processed_source = metadata[i].get("source")
        source = SOURCE_MAP.get(processed_source, processed_source)
        page = metadata[i]["page"]

        context += f"""
TEXT:
{chunk}

SOURCE:
{source} page {page}

"""

    prompt = f"""
You are a financial assistant.

Conversation so far:
{history}

Mode: {mode}
Response Style: {response_style}

STRICT RULES (FOLLOW EXACTLY):

GLOBAL STYLE:
- Write for a non-expert user in simple everyday language.
- Keep sentences short and clear.
- Avoid heavy jargon; if a technical term is needed, define it in the same sentence.
- Prefer practical meaning over textbook wording.

EXPLAIN:
- Give detailed explanations (3–5 sentences)
- Explain clearly like teaching a beginner
- Include practical examples where relevant
- Mention important limits, rules, or conditions if applicable
- Avoid generic statements

GUIDE:
- Give step-by-step actionable guidance
- Use clean bullet points
- Avoid numbering unless necessary
- Put ALL steps inside "key_points"
- Each step should be short and actionable
- Do NOT start with a long paragraph
- Include what to do if stuck
- Do NOT repeat the same content in both "answer" and "key_points"

INLINE_WHATIF:
- Maximum 2–4 lines
- Clearly mention risk + consequence
- No detailed explanation

REDIRECT:
- Do NOT answer
- ONLY say: "This scenario is better handled in What-If Simulation"

RESPONSE STYLE CONTROL:

SHORT:
- Only "answer" (1–2 lines)

POINTS:
- "answer" should be 1 short line
- ALL content must go in "key_points"

DETAILED:
- Explanation in "answer"
- Optional points in "key_points"

IMPORTANT:
- Do NOT put lists inside "answer"
- Use "key_points" for lists/steps only

Return JSON:

Rules:
- "answer" must be plain text only
- Do NOT include {{}}, [], **, -, or any formatting symbols
- Do NOT include lists inside "answer"
- "key_points" must be a clean list of simple strings
- Each key point must be plain text (no symbols like -, *, **)
- Never return JSON inside JSON

Format EXACTLY like:

{{
 "answer": "Simple clean explanation",
 "key_points": [
  "Point one",
  "Point two",
  "Point three"
 ]
}}

Context:
{context}

Question:
{question}
"""

    try:
        response = chat_complete_with_retry(
            client,
            model="grok-4.20",
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as exc:
        logger.exception("Grok API call failed: %s", exc)
        # Propagate exception to allow outer fallback to trigger
        raise

    try:
        content = response.choices[0].message.content.strip()
    except Exception:
        logger.warning("Mistral response missing expected content structure: %s", getattr(response, 'raw', response))
        raise Exception("Empty or invalid model response")
    content = content.replace("json", "").replace("```", "").strip()

    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        cleaned_json = content[start:end]

        data = json.loads(cleaned_json)

        if not isinstance(data, dict):
          raise Exception()

    except:
        data = {
            "answer": content,
            "key_points": []
    }

    if isinstance(data.get("answer"), str) and data["answer"].strip().startswith("{"):
       try:
           data = json.loads(data["answer"])
       except:
        pass

    sources = []
    for i in context_chunks:
        file_name = SOURCE_MAP.get(metadata[i].get("source"), metadata[i].get("source"))
        page_num = metadata[i]["page"]
        sources.append(
            {
                "file": file_name,
                "page": page_num,
                "url": f"/docs/{file_name}#page={page_num}",
                "reliability": "HIGH" if file_name in TRUSTED_DOCS else "MEDIUM",
            }
        )
    deduped_sources = []
    seen_sources = set()
    for item in sources:
        key = (item.get("file"), item.get("page"))
        if key in seen_sources:
            continue
        seen_sources.add(key)
        deduped_sources.append(item)
    data["sources"] = deduped_sources

    links = helpful_links_for_question(question, data["sources"])
    deduped_links = []
    seen_links = set()
    for item in links:
        key = (item.get("title"), item.get("url"))
        if key in seen_links:
            continue
        seen_links.add(key)
        deduped_links.append(item)

    def clean_text(text):
        text = str(text)
        return text.replace("{", "").replace("}", "").replace("[", "").replace("]", "").replace("*", "")

    if "answer" in data:
        data["answer"] = normalize_answer_text(clean_text(data["answer"]))

    if "key_points" in data:
        data["key_points"] = normalize_key_points([clean_text(str(p)) for p in data["key_points"]])


    data["helpful_links"] = deduped_links
    data["source_reliability"] = source_reliability_summary(deduped_sources)
    data["mode"] = mode
    data["is_off_topic"] = False
    data["retrieval_mode"] = "BM25_ONLY" if model_load_error else "HYBRID"

    data.setdefault("rule_matches", [])
    data.setdefault("rules_checked", 0)
    data.setdefault("rule_summary", "No rule evaluation performed.")

    # ====== FINTRIX RULE ENGINE CROSS-VALIDATION ======
    try:
        from backend.database import SessionLocal
        from backend.rules.engine import evaluate_for_scenario

        db = SessionLocal()
        try:
            amount_match = re.search(r'(\d+[,\d]*)', question.replace(",", ""))
            amount = int(amount_match.group(1)) if amount_match else 0

            q = question.lower()
            event_types = []
            if any(w in q for w in ["fraud", "scam", "phishing", "unauthorized"]):
                event_types.append("fraud")
            if any(w in q for w in ["loan", "default", "emi", "npa"]):
                event_types.append("loan_default")
            if any(w in q for w in ["forex", "foreign", "lrs", "remittance", "abroad"]):
                event_types.append("foreign_transfer")
            if any(w in q for w in ["insider", "trading", "stock", "sebi"]):
                event_types.append("investment_violation")
            if any(w in q for w in ["ai", "algorithm", "bias", "digital lending"]):
                event_types.append("ai_bias")

            rule_result = evaluate_for_scenario(
                db=db,
                question=question,
                event_types=event_types,
                amount=amount,
                user_id=None,
                debug=False,
            )

            summary = rule_result.get("rule_summary", {})
            data["rule_matches"] = rule_result.get("matched_rules", [])
            data["rules_checked"] = rule_result.get("total_rules", 0)
            data["rule_summary"] = summary.get("summary", "No rule evaluation performed.")
            data["rule_reason"] = summary.get("reason", "")
            data["compliance_status"] = summary.get("status", "No Match")

            if data["rule_matches"]:
                # Keep the answer user-friendly and avoid prepending technical
                # compliance status text into the first sentence.
                note = summary.get("summary", "")
                if note:
                    existing_points = data.get("key_points") if isinstance(data.get("key_points"), list) else []
                    data["key_points"] = normalize_key_points([f"Compliance check: {note}"] + existing_points)
        finally:
            db.close()
    except Exception:
        data["rule_matches"] = []
        data["rules_checked"] = 0
        data["rule_summary"] = "Rule evaluation unavailable."
        data["compliance_status"] = "Unavailable"

    return data
