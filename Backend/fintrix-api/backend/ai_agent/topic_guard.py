"""Fast topic guard helpers for FinTrix AI requests."""

import re


FINANCE_KEYWORDS = (
    "finance",
    "financial",
    "fintech",
    "bank",
    "banking",
    "payment",
    "payments",
    "upi",
    "wallet",
    "credit card",
    "debit card",
    "loan",
    "mortgage",
    "interest rate",
    "apr",
    "investment",
    "investing",
    "portfolio",
    "asset allocation",
    "stock",
    "stocks",
    "share market",
    "equity",
    "bond",
    "mutual fund",
    "etf",
    "forex",
    "foreign exchange",
    "remittance",
    "hedging",
    "derivative",
    "futures",
    "options",
    "commodity market",
    "insurance",
    "premium",
    "claim settlement",
    "cryptocurrency",
    "crypto",
    "blockchain",
    "token",
    "tax",
    "taxation",
    "gst",
    "income tax",
    "audit",
    "auditing",
    "accounting",
    "balance sheet",
    "cash flow",
    "p&l",
    "profit and loss",
    "treasury",
    "lrs",
    "budget",
    "budgeting",
    "fiscal",
    "liquidity",
    "capital adequacy",
    "risk management",
    "market risk",
    "credit risk",
    "operational risk",
    "compliance",
    "regulatory",
    "regulation",
    "sebi",
    "rbi",
    "basel iii",
    "aml",
    "kyc",
    "fema",
    "anti money laundering",
    "financial planning",
    "retirement planning",
    "economic policy",
    "monetary policy",
    "inflation",
    "recession",
    "cds",
    "credit default swap",
    "npa",
    "emi",
    "ifsc",
    "neft",
    "rtgs",
    "imps",
    "demat",
    "ipo",
    "sip",
    "nav",
    "fd",
    "rd",
    "ulip",
    "sbi",
    "state bank of india",
)

NON_FINANCE_KEYWORDS = (
    "recipe",
    "cooking",
    "restaurant",
    "weather",
    "temperature",
    "movie",
    "cinema",
    "actor",
    "celebrity",
    "cricket",
    "football",
    "sports",
    "match score",
    "video game",
    "gaming",
    "travel",
    "tourism",
    "fashion",
    "makeup",
    "pet care",
    "gardening",
    "homework",
    "poem",
    "song lyrics",
    "food",
    "snack",
    "recipe",
    "vada pav",
    "pizza",
    "burger",
    "restaurant",
    "menu",
    "cricket score",
    "movie review",
)

GREETING_PATTERNS = (
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "thanks",
    "thank you",
    "okay",
    "ok",
    "can you help me",
    "help me",
    "are you there",
)

OFF_TOPIC_MESSAGE = (
    "I'm FinTrix, a finance and regulatory intelligence assistant. "
    "I can only help with finance, compliance, market, and regulatory "
    "questions. Please ask me something related to those domains."
)

WELCOME_MESSAGE = (
    "Hi, I'm FinTrix. I can help with finance, compliance, markets, "
    "banking, taxation, insurance, and regulatory questions. Ask me "
    "about topics like Basel III, SEBI rules, portfolio risk, or "
    "payment compliance."
)


def normalize_question(question: str) -> str:
    """Normalize user input for guard checks."""
    return re.sub(r"\s+", " ", (question or "").strip().lower())


def contains_keyword(question: str, keywords: tuple[str, ...]) -> bool:
    """Check whether any keyword appears in the question."""
    normalized = normalize_question(question)
    return any(keyword in normalized for keyword in keywords)


def is_greeting_or_clarifier(question: str) -> bool:
    """Detect short greetings and lightweight clarifying prompts."""
    normalized = normalize_question(question)
    if not normalized:
        return True
    if normalized in GREETING_PATTERNS:
        return True
    short_words = normalized.split()
    known_short_messages = {"yo", "hello there", "thanks a lot"}
    if len(short_words) <= 4 and normalized in known_short_messages:
        return True
    return normalized.endswith("?") and normalized[:-1] in GREETING_PATTERNS


def is_finance_related(question: str) -> bool:
    """Return True only when the question appears finance-related."""
    normalized = normalize_question(question)

    # Short acronyms/terms commonly used in finance chats.
    if normalized in {
        "cds",
        "npa",
        "emi",
        "ifsc",
        "neft",
        "rtgs",
        "imps",
        "ipo",
        "sip",
        "nav",
        "fd",
        "rd",
        "ulip",
        "sbi",
        "rbi",
        "sebi",
    }:
        return True

    if contains_keyword(question, FINANCE_KEYWORDS):
        return True

    # Check for numbers + finance context (e.g. "10 lakh abroad")
    if re.search(r'\d+', normalized) and any(w in normalized for w in ["lakh", "crore", "cr", "lac", "million", "usd", "inr", "transfer", "send"]):
        return True

    if contains_keyword(question, NON_FINANCE_KEYWORDS):
        return False

    # If the question is long enough and doesn't look like obvious garbage/off-topic,
    # we might want to let it through to the LLM which is better at judging.
    # However, to maintain the guard's intent, we stay relatively strict but
    # allow common finance sentence structures.
    if any(w in normalized for w in ["how much", "can i", "what is the limit", "what are the rules"]):
        return True

    return False


def classify_question_scope(question: str) -> str:
    """Classify a question as greeting, finance, or off-topic."""
    if is_greeting_or_clarifier(question):
        return "greeting"
    if is_finance_related(question):
        return "finance"
    return "off_topic"


def build_welcome_response() -> dict:
    """Build a friendly finance-domain welcome response."""
    return {
        "answer": WELCOME_MESSAGE,
        "key_points": [
            "Ask about banking rules, investments, taxation, or compliance.",
            (
                "I can explain financial concepts, regulations, "
                "and market topics."
            ),
            "You can also ask scenario-based questions about risk and controls.",
        ],
        "sources": [],
        "helpful_links": [],
        "mode": "WELCOME",
        "is_off_topic": False,
        "rule_matches": [],
        "rules_checked": 0,
        "rule_summary": "Welcome message returned.",
    }


def build_off_topic_response() -> dict:
    """Build a structured response for off-topic questions."""
    return {
        "answer": OFF_TOPIC_MESSAGE,
        "key_points": [],
        "sources": [],
        "helpful_links": [],
        "mode": "OUT_OF_SCOPE",
        "is_off_topic": True,
        "rule_matches": [],
        "rules_checked": 0,
        "rule_summary": "Question blocked by the finance topic guard.",
    }
