"""Tests for the FinTrix AI topic guard."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai_agent.topic_guard import (
    build_welcome_response,
    classify_question_scope,
    is_finance_related,
)


def test_finance_question_passes_guard():
    """Finance questions should pass the topic guard."""
    question = (
        "How does Basel III capital adequacy affect "
        "bank liquidity risk?"
    )
    assert is_finance_related(question) is True
    assert classify_question_scope(question) == "finance"


def test_off_topic_question_is_blocked():
    """Clearly off-topic questions should be blocked."""
    question = "Can you share a pasta recipe for dinner tonight?"
    assert is_finance_related(question) is False
    assert classify_question_scope(question) == "off_topic"


def test_greeting_returns_welcome_path():
    """Greetings should return the welcome path instead of being blocked."""
    response = build_welcome_response()
    assert classify_question_scope("hello") == "greeting"
    assert response["is_off_topic"] is False
    assert "finance" in response["answer"].lower()


def test_ambiguous_question_is_allowed():
    """Ambiguous questions should be handled permissively."""
    question = "Should I be worried about long-term risk here?"
    assert is_finance_related(question) is True
    assert classify_question_scope(question) == "finance"
