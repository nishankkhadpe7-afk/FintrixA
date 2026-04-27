import os
from dotenv import load_dotenv
import re
import json
from pathlib import Path
from backend.mistral_client import get_mistral_client

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

client = get_mistral_client()

FINANCIAL_KEYWORDS = {
    "bank", "banking", "loan", "emi", "npa", "credit", "debit", "fraud", "scam",
    "transaction", "money", "payment", "pay", "upi", "rbi", "fema", "lrs", "forex",
    "remittance", "tax", "tds", "tcs", "compliance", "financial", "stock", "share",
    "trading", "sebi", "bond", "investment", "aml", "account", "withdrawal", "deposit",
    "transfer", "abroad", "education", "tuition", "fees",
}


def extract_amount(text):
    normalized = text.lower().replace(",", "")
    match = re.search(r'(\d+(?:\.\d+)?)\s*(crore|cr|lakh|lac|lakhs|lacs|million|thousand|k)?', normalized)
    if match:
        value = float(match.group(1))
        unit = (match.group(2) or "").strip()

        multiplier_map = {
            "crore": 10000000,
            "cr": 10000000,
            "lakh": 100000,
            "lac": 100000,
            "lakhs": 100000,
            "lacs": 100000,
            "million": 1000000,
            "thousand": 1000,
            "k": 1000,
        }

        return int(value * multiplier_map.get(unit, 1))
    return 0


def detect_event_keywords(question):
    q = question.lower()
    event_types = []

    if any(word in q for word in ["fraud", "scam", "phishing", "unauthorized", "otp", "cyber"]):
        event_types.append("fraud")
    if any(word in q for word in ["loan", "emi", "default", "npa", "borrower"]):
        event_types.append("loan_default")
    if any(word in q for word in ["foreign", "abroad", "remittance", "forex", "lrs", "fema", "transfer"]):
        event_types.append("foreign_transfer")
    if any(word in q for word in ["stock", "share", "trading", "sebi", "insider", "investment"]):
        event_types.append("investment_violation")
    if any(word in q for word in ["algorithm", "ai bias", "digital lending", "model bias"]):
        event_types.append("ai_bias")

    return event_types or ["normal"]


def detect_event_llm(question):
    prompt = f"""
Identify ALL financial events in the scenario.

Question:
{question}

Return STRICT JSON:

{{
"event_types": ["loan_default","fraud"],
"confidence": 0-1,
"reason": "why these classifications"
}}
"""

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content.strip()

    start = content.find("{")
    end = content.rfind("}") + 1

    try:
        data = json.loads(content[start:end])
        return data["event_types"], data["confidence"], data["reason"]
    except:
        return ["normal"], 0.5, "fallback classification"


def risk_color(risk):
    if risk == "High":
        return "red"
    if risk == "Medium":
        return "orange"
    if risk == "Low":
        return "green"
    return "gray"


def is_financial_query(question):
    q = question.lower()
    return any(keyword in q for keyword in FINANCIAL_KEYWORDS)


def out_of_scope_response(question):
    return {
        "analysis": "This query does not describe a financial or compliance scenario, so the What-If engine cannot evaluate it meaningfully.",
        "compliance_status": "Not Applicable",
        "risk_level": "Low",
        "risk_score": 0,
        "confidence": 1.0,
        "reason": "Non-financial query with no regulatory or compliance implications.",
        "risk_color": "green",
        "what_could_happen_next": {
            "immediate": ["No financial compliance consequence identified."],
            "regulatory": ["No RBI, SEBI, tax, or banking rule applies to this query."],
            "tax": [],
            "worst_case": []
        },
        "what_should_you_do": {
            "immediate_actions": ["Ask a financial or compliance scenario to use this tool effectively."],
            "compliance_actions": [],
            "risk_mitigation": [],
            "preventive_measures": []
        },
        "timeline": ["No financial scenario timeline identified."],
        "fraud_liability": "Not applicable",
        "regulations": ["No applicable financial regulations"],
        "rule_matches": [],
        "rules_checked": 0,
        "rule_summary": "Out of scope for financial what-if analysis.",
        "rule_override": False,
    }


def derive_rule_decision(rule_result):
    summary = rule_result.get("rule_summary", {})
    status = summary.get("status", "Compliant")
    risk = summary.get("risk_level", "Low")
    reason = summary.get("reason", "No active compliance rules were triggered by the scenario.")
    highest_severity = summary.get("highest_severity")

    score_map = {
        "Low": 25,
        "Medium": 55,
        "High": 85,
    }
    if highest_severity == "critical":
        score = 95
    else:
        score = score_map.get(risk, 40)

    return {
        "status": status,
        "risk": risk,
        "reason": reason,
        "score": score,
        "summary": summary.get("summary", reason),
    }


def risk_score_engine(event_types, amount, question):
    score = 0
    text = question.lower()

    if "fraud" in event_types:
        score += 40
    if "loan_default" in event_types:
        score += 35
    if "investment_violation" in event_types:
        score += 40
    if amount > 1000000:
        score += 10
    if amount > 10000000:
        score += 15
    if "undeclared" in text:
        score += 20
    if "multiple" in text:
        score += 10

    return min(score, 100)


def timeline_engine(event_types, question):
    timeline = []

    if "fraud" in event_types:
        timeline += [
            "User interacts with fraudulent source",
            "Credentials or OTP compromised",
            "Unauthorized transaction executed",
            "User reports to bank",
            "Bank investigates liability"
        ]

    if "loan_default" in event_types:
        timeline += [
            "Loan disbursed",
            "Financial stress occurs",
            "EMI missed",
            "Account overdue",
            "Loan classified as NPA"
        ]

    if "foreign_transfer" in event_types:
        timeline += [
            "User initiates transfer",
            "Bank checks LRS eligibility",
            "Documents verified",
            "Transfer processed",
            "Reported under RBI"
        ]

    if "investment_violation" in event_types:
        timeline += [
            "Investment made",
            "Source not declared",
            "Transaction flagged",
            "Investigation initiated",
            "Penalty/legal action possible"
        ]

    return timeline if timeline else ["No clear timeline identified"]


def fraud_liability_engine(event_types, question):
    text = question.lower()

    if "fraud" not in event_types:
        return "Not applicable"

    if "phishing" in text or "otp" in text:
        return "Customer liable (credential sharing/negligence)"

    if "immediately" in text or "instant" in text:
        return "Zero liability (reported promptly)"

    if "delay" in text or "late" in text:
        return "Limited liability depending on delay"

    return "Liability subject to bank investigation"


def regulation_mapping(event_types, question):
    rules = []

    if "loan_default" in event_types:
        rules += [
            "RBI IRAC Norms",
            "Insolvency and Bankruptcy Code (IBC)"
        ]

    if "fraud" in event_types:
        rules += [
            "RBI Customer Protection Circular",
            "IT Act 2000"
        ]

    if "ai_bias" in event_types:
        rules += [
            "RBI Digital Lending Guidelines",
            "Fair Lending Practices"
        ]

    if "foreign_transfer" in event_types:
        rules += [
            "RBI Liberalised Remittance Scheme (LRS)",
            "Income Tax Act - TCS"
        ]

    if "investment_violation" in event_types:
        rules += [
            "Prevention of Money Laundering Act (PMLA)",
            "Income Tax Act"
        ]

    return list(set(rules)) if rules else ["General Banking Regulations"]


def consequence_engine(event_types, amount, question):
    consequences = []

    if "loan_default" in event_types:
        consequences += [
            "Loan classified as NPA",
            "Credit score drops",
            "Recovery/legal action possible"
        ]

    if "fraud" in event_types:
        consequences += [
            "Financial loss possible",
            "Liability depends on reporting time",
            "Bank investigation required"
        ]

    if "ai_bias" in event_types:
        consequences += [
            "Regulatory violation risk",
            "Customer discrimination impact",
            "Model audit required"
        ]

    if "foreign_transfer" in event_types and "delay" in question.lower():
        consequences += [
        "Late reporting may trigger Income Tax notice",
        "Mismatch in Form 26AS possible",
        "Bank compliance flag may increase scrutiny",
        "Penalty risk under FEMA for delayed declaration"
    ]

    if "investment_violation" in event_types:
        consequences += [
            "Tax penalties possible",
            "AML investigation risk",
            "Legal consequences"
        ]

    return consequences if consequences else ["No major consequence identified"]


def rule_engine(amount, event_types, question):
    if "fraud" in event_types:
        return "Non-Compliant", "High", "Unauthorized transaction / fraud"

    if "loan_default" in event_types:
        return "Non-Compliant", "High", "Loan default leading to NPA"

    if "ai_bias" in event_types:
        return "Review Required", "High", "Algorithmic bias risk"

    if "foreign_transfer" in event_types:
        if amount > 25000000:
            return "Non-Compliant", "High", "Exceeds RBI LRS limit"
        elif amount > 10000000:
            return "Compliant", "Medium", "High-value transfer"
        return "Compliant", "Low", "Within LRS limit"

    if "investment_violation" in event_types:
        return "Non-Compliant", "High", "Undeclared / illegal investment"

    return "Compliant", "Low", "Normal case"


def _generate_full_response(
    question,
    status,
    risk,
    reason,
    consequences,
    regulations,
    event_types,
    confidence,
    event_reason,
    color,
    score,
    timeline,
    liability
):
    prompt = f"""
You are an expert financial compliance and risk advisor for India.

Analyze the scenario deeply and give a realistic, practical, and structured response.

Explain like:
"Here's what's happening, here's the risk, and here's what you should do"

Analyze the scenario deeply and give a realistic, practical, and structured response.

Scenario:
{question}

Detected Events: {event_types}
Confidence: {confidence}
Reason: {event_reason}

Decision:
Compliance Status: {status}
Risk Level: {risk}
Risk Score: {score}
Reason: {reason}

Timeline:
{timeline}

Fraud Liability:
{liability}

Consequences:
{consequences}

Regulations:
{regulations}

---

Return STRICT JSON:

{{
"analysis": "Explain in 2–3 concise sentences what is happening. Avoid long paragraphs.(practical tone)",
"compliance_status": "{status}",
"risk_level": "{risk}",
"risk_score": {score},
"confidence": {confidence},
"reason": "{reason}",

"what_could_happen_next": {{
    "immediate": ["short term effects"],
    "regulatory": ["mention FEMA, RBI, IT Act where relevant"],
    "tax": ["TCS, penalties, notices if applicable"],
    "worst_case": ["extreme but realistic outcomes"]
}},

"what_should_you_do": {{
    "immediate_actions": ["urgent steps"],
    "compliance_actions": ["legal / reporting steps"],
    "risk_mitigation": ["reduce damage"],
    "preventive_measures": ["avoid future issues"]
}},

"timeline": {json.dumps(timeline)},
"fraud_liability": "{liability}",
"regulations": {json.dumps(regulations)}
}}
"""

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content
        content = content.replace("json", "").strip()

        start = content.find("{")
        end = content.rfind("}") + 1

        parsed = json.loads(content[start:end])
        parsed["confidence"] = confidence
        parsed["risk_color"] = color
        return parsed
    except Exception as exc:
        raise RuntimeError("LLM response unavailable for what-if generation") from exc


def _generate_local_fallback_response(
    question,
    status,
    risk,
    reason,
    consequences,
    regulations,
    confidence,
    color,
    score,
    timeline,
    liability
):
    immediate_actions = []
    compliance_actions = []
    risk_mitigation = []

    if "foreign" in question.lower() or "abroad" in question.lower() or "remittance" in question.lower():
        immediate_actions.append("Pause the transfer until the purpose code and declaration details are confirmed with the bank.")
        compliance_actions.append("Ask the authorized dealer bank which FEMA or LRS declaration documents are required for this transfer.")
        risk_mitigation.append("Keep transfer records, beneficiary details, and source-of-funds documents ready before retrying.")

    if "loan" in question.lower() or "emi" in question.lower() or "default" in question.lower():
        immediate_actions.append("Review the repayment timeline and outstanding amount immediately.")
        compliance_actions.append("Contact the lender to discuss restructuring, overdue classification, or reporting consequences.")
        risk_mitigation.append("Document all lender communication and proposed settlement steps.")

    if "fraud" in question.lower() or "scam" in question.lower() or "unauthorized" in question.lower():
        immediate_actions.append("Report the transaction to the bank immediately and block affected channels.")
        compliance_actions.append("File a formal fraud complaint and preserve evidence such as messages, numbers, and timestamps.")
        risk_mitigation.append("Reset credentials and review linked accounts or devices for further compromise.")

    if not immediate_actions:
        immediate_actions.append("Review the scenario details carefully before taking action.")
    if not compliance_actions:
        compliance_actions.append("Confirm the applicable reporting and documentation requirements with the relevant institution.")
    if not risk_mitigation:
        risk_mitigation.append("Keep records of the transaction and all supporting documents.")

    analysis = (
        f"{reason} Based on the scenario you entered, the current local fallback engine classifies this as "
        f"{risk.lower()} risk with a {status.lower()} posture. This response is generated without the live "
        f"Mistral narrative layer, but it still uses the rule engine and deterministic scenario heuristics."
    )

    return {
        "analysis": analysis,
        "compliance_status": status,
        "risk_level": risk,
        "risk_score": score,
        "confidence": confidence,
        "reason": reason,
        "risk_color": color,
        "what_could_happen_next": {
            "immediate": consequences[:3] if consequences else ["No immediate consequence identified."],
            "regulatory": regulations[:3],
            "tax": [item for item in consequences if "tax" in item.lower() or "tcs" in item.lower() or "notice" in item.lower()][:3],
            "worst_case": consequences[-2:] if consequences else [],
        },
        "what_should_you_do": {
            "immediate_actions": immediate_actions[:3],
            "compliance_actions": compliance_actions[:3],
            "risk_mitigation": risk_mitigation[:3],
            "preventive_measures": [
                "Verify reporting obligations before completing high-risk financial actions.",
                "Retain supporting documents and confirmation messages.",
                "Escalate to the bank, broker, or advisor early when the scenario looks non-compliant.",
            ],
        },
        "timeline": timeline,
        "fraud_liability": liability,
        "regulations": regulations,
        "mode": "LOCAL_FALLBACK",
    }


def what_if_agent(question):
    if not is_financial_query(question):
        return out_of_scope_response(question)

    amount = extract_amount(question)

    try:
        event_types, confidence, event_reason = detect_event_llm(question)
    except:
        event_types = detect_event_keywords(question)
        confidence = 0.65 if event_types != ["normal"] else 0.5
        event_reason = "keyword fallback classification"

    consequences = consequence_engine(event_types, amount, question)
    regulations = regulation_mapping(event_types, question)
    timeline = timeline_engine(event_types, question)
    liability = fraud_liability_engine(event_types, question)

    rule_result = {"matched_rules": [], "total_rules": 0, "rule_summary": {}}
    try:
        from backend.database import SessionLocal
        from backend.rules.engine import evaluate_for_scenario

        db = SessionLocal()
        try:
            rule_result = evaluate_for_scenario(
                db=db,
                question=question,
                event_types=event_types,
                amount=amount,
                user_id=None,
                debug=False
            )
        finally:
            db.close()
    except Exception:
        rule_result = {"matched_rules": [], "total_rules": 0, "rule_summary": {}}

    rule_decision = derive_rule_decision(rule_result)
    status = rule_decision["status"]
    risk = rule_decision["risk"]
    reason = rule_decision["reason"]
    score = max(risk_score_engine(event_types, amount, question), rule_decision["score"])
    color = risk_color(risk)

    try:
        response = _generate_full_response(
            question, status, risk, reason, consequences,
            regulations, event_types, confidence, event_reason,
            color, score, timeline, liability
        )
    except Exception:
        response = _generate_local_fallback_response(
            question, status, risk, reason, consequences,
            regulations, confidence, color, score, timeline, liability
        )

    response["rule_matches"] = rule_result.get("matched_rules", [])
    response["rules_checked"] = rule_result.get("total_rules", 0)
    response["rule_summary"] = rule_decision["summary"]
    response.setdefault("mode", "LLM")

    if response["rule_matches"]:
        response["analysis"] = f"{rule_decision['summary']} {response.get('analysis', '')}".strip()

    if rule_decision["status"] != "Compliant":
        response["rule_override"] = True
        response["rule_override_reason"] = rule_decision["summary"]
    else:
        response["rule_override"] = False

    return response
