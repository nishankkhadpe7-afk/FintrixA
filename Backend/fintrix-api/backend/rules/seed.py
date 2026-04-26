"""
Seed data for the integrated Fintrix Rule Engine.
Populates the compliance_rules table with real Indian financial compliance rules.
"""

import json
from backend.database import SessionLocal
from backend.rules.models import ComplianceRule


SEED_RULES = [
    # ========== FOREX / LRS RULES ==========
    {
        "rule_id": "FOREX-001",
        "domain": "forex",
        "type": "threshold",
        "title": "LRS Annual Limit Exceeded",
        "description": "Under RBI's Liberalised Remittance Scheme, individuals can remit up to USD 2,50,000 per financial year. Transactions exceeding this are non-compliant.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "forex"},
                {"field": "amount", "operator": ">", "value": 25000000}
            ]
        }),
        "action": "block",
        "source_document": "RBI Master Direction on LRS",
        "source_url": "https://www.rbi.org.in",
        "regulator": "RBI",
        "severity": "critical"
    },
    {
        "rule_id": "FOREX-002",
        "domain": "forex",
        "type": "reporting",
        "title": "High-Value Foreign Transfer Reporting",
        "description": "Foreign transfers above ₹10 lakh require enhanced due diligence and TCS collection at 5% (or 20% without PAN).",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "forex"},
                {"field": "amount", "operator": ">", "value": 1000000}
            ]
        }),
        "action": "flag",
        "source_document": "Income Tax Act - TCS Provisions",
        "source_url": "https://www.incometax.gov.in",
        "regulator": "IT",
        "severity": "high"
    },
    {
        "rule_id": "FOREX-003",
        "domain": "forex",
        "type": "restriction",
        "title": "Undeclared Foreign Transfer",
        "description": "All foreign remittances must be declared to the authorized dealer bank. Undeclared transfers violate FEMA regulations.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "forex"},
                {"field": "declared", "operator": "==", "value": False}
            ]
        }),
        "action": "block",
        "source_document": "FEMA Act 1999",
        "source_url": "https://www.rbi.org.in",
        "regulator": "RBI",
        "severity": "critical"
    },
    {
        "rule_id": "FOREX-004",
        "domain": "forex",
        "type": "threshold",
        "title": "Medium Risk Foreign Transfer",
        "description": "Foreign transfers between ₹7 lakh and ₹10 lakh are subject to TCS at 5% above ₹7 lakh threshold.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "forex"},
                {"field": "amount", "operator": ">=", "value": 700000},
                {"field": "amount", "operator": "<=", "value": 10000000}
            ]
        }),
        "action": "flag",
        "source_document": "Finance Act 2023 - TCS Amendment",
        "source_url": "https://www.incometax.gov.in",
        "regulator": "IT",
        "severity": "medium"
    },

    # ========== LENDING RULES ==========
    {
        "rule_id": "LEND-001",
        "domain": "lending",
        "type": "threshold",
        "title": "NPA Classification - 90 Day Default",
        "description": "As per RBI IRAC norms, a loan account is classified as Non-Performing Asset (NPA) if interest/principal remains overdue for 90 days.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "lending"},
                {"field": "event_loan_default", "operator": "==", "value": True}
            ]
        }),
        "action": "flag",
        "source_document": "RBI IRAC Norms",
        "source_url": "https://www.rbi.org.in",
        "regulator": "RBI",
        "severity": "high"
    },
    {
        "rule_id": "LEND-002",
        "domain": "lending",
        "type": "reporting",
        "title": "Large Loan Default Reporting",
        "description": "Loan defaults above ₹1 crore must be reported to CRILC (Central Repository of Information on Large Credits).",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "lending"},
                {"field": "event_loan_default", "operator": "==", "value": True},
                {"field": "amount", "operator": ">", "value": 10000000}
            ]
        }),
        "action": "block",
        "source_document": "RBI CRILC Reporting Framework",
        "source_url": "https://www.rbi.org.in",
        "regulator": "RBI",
        "severity": "critical"
    },
    {
        "rule_id": "LEND-003",
        "domain": "lending",
        "type": "eligibility",
        "title": "Digital Lending Fair Practice",
        "description": "Digital lending platforms must disclose all-in cost including APR, processing fees and penalties upfront. Non-disclosure is a violation.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "lending"},
                {"field": "event_ai_bias", "operator": "==", "value": True}
            ]
        }),
        "action": "review",
        "source_document": "RBI Digital Lending Guidelines 2022",
        "source_url": "https://www.rbi.org.in",
        "regulator": "RBI",
        "severity": "high"
    },

    # ========== FRAUD RULES ==========
    {
        "rule_id": "FRAUD-001",
        "domain": "general",
        "type": "restriction",
        "title": "Unauthorized Transaction - Zero Liability",
        "description": "If fraud is due to bank negligence or third-party breach, customer has zero liability as per RBI Circular on Customer Protection.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "event_fraud", "operator": "==", "value": True},
                {"field": "fraud_indicator", "operator": "==", "value": True}
            ]
        }),
        "action": "flag",
        "source_document": "RBI Customer Protection Circular 2017",
        "source_url": "https://www.rbi.org.in",
        "regulator": "RBI",
        "severity": "critical"
    },
    {
        "rule_id": "FRAUD-002",
        "domain": "general",
        "type": "reporting",
        "title": "Fraud Reporting Timeline",
        "description": "Customer must report unauthorized transactions within 3 working days for zero liability. Delay increases customer liability.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "event_fraud", "operator": "==", "value": True}
            ]
        }),
        "action": "flag",
        "source_document": "RBI Customer Protection Circular 2017",
        "source_url": "https://www.rbi.org.in",
        "regulator": "RBI",
        "severity": "high"
    },

    # ========== TRADING / INVESTMENT RULES ==========
    {
        "rule_id": "TRADE-001",
        "domain": "trading",
        "type": "restriction",
        "title": "Insider Trading Prohibition",
        "description": "Trading based on Unpublished Price Sensitive Information (UPSI) is prohibited under SEBI (PIT) Regulations 2015.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "trading"},
                {"field": "event_investment_violation", "operator": "==", "value": True}
            ]
        }),
        "action": "block",
        "source_document": "SEBI (PIT) Regulations 2015",
        "source_url": "https://www.sebi.gov.in",
        "regulator": "SEBI",
        "severity": "critical"
    },
    {
        "rule_id": "TRADE-002",
        "domain": "trading",
        "type": "reporting",
        "title": "Large Trade Reporting",
        "description": "Single trades exceeding ₹10 crore must be reported for market surveillance per SEBI norms.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "trading"},
                {"field": "amount", "operator": ">", "value": 100000000}
            ]
        }),
        "action": "flag",
        "source_document": "SEBI Market Surveillance Framework",
        "source_url": "https://www.sebi.gov.in",
        "regulator": "SEBI",
        "severity": "high"
    },

    # ========== ANTI-MONEY LAUNDERING ==========
    {
        "rule_id": "AML-001",
        "domain": "general",
        "type": "reporting",
        "title": "Suspicious Transaction Report (STR)",
        "description": "Cash transactions above ₹10 lakh (or series of connected transactions) must trigger STR filing under PMLA.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "amount", "operator": ">", "value": 1000000},
                {"field": "declared", "operator": "==", "value": False}
            ]
        }),
        "action": "block",
        "source_document": "Prevention of Money Laundering Act 2002",
        "source_url": "https://www.fiu-india.gov.in",
        "regulator": "FIU",
        "severity": "critical"
    },
    {
        "rule_id": "AML-002",
        "domain": "general",
        "type": "reporting",
        "title": "Cash Transaction Report (CTR)",
        "description": "All cash transactions above ₹10 lakh in a month must be reported under PMLA rules.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "amount", "operator": ">", "value": 1000000}
            ]
        }),
        "action": "flag",
        "source_document": "PMLA Rules - CTR Requirements",
        "source_url": "https://www.fiu-india.gov.in",
        "regulator": "FIU",
        "severity": "medium"
    },

    # ========== BONDS RULES ==========
    {
        "rule_id": "BOND-001",
        "domain": "bonds",
        "type": "eligibility",
        "title": "Sovereign Gold Bond Limit",
        "description": "Individual investors can hold max 4kg of gold per FY under SGB scheme. HUFs can hold 4kg, trusts 20kg.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "domain", "operator": "==", "value": "bonds"}
            ]
        }),
        "action": "review",
        "source_document": "RBI Sovereign Gold Bond Scheme",
        "source_url": "https://www.rbi.org.in",
        "regulator": "RBI",
        "severity": "low"
    },

    # ========== TAX COMPLIANCE ==========
    {
        "rule_id": "TAX-001",
        "domain": "general",
        "type": "threshold",
        "title": "TDS on Cash Withdrawal",
        "description": "Cash withdrawals exceeding ₹1 crore in a year attract 2% TDS under Section 194N. For non-filers, threshold is ₹20 lakh at 2% and ₹1 crore at 5%.",
        "canonical_rule": json.dumps({
            "logic": "AND",
            "conditions": [
                {"field": "amount", "operator": ">", "value": 10000000}
            ]
        }),
        "action": "flag",
        "source_document": "Income Tax Act Section 194N",
        "source_url": "https://www.incometax.gov.in",
        "regulator": "IT",
        "severity": "medium"
    }
]


def seed_rules():
    """Seed the database with compliance rules."""
    db = SessionLocal()
    try:
        existing = db.query(ComplianceRule).count()
        if existing > 0:
            print(f"Database already has {existing} rules. Skipping seed.")
            return existing

        for rule_data in SEED_RULES:
            rule = ComplianceRule(**rule_data)
            db.add(rule)

        db.commit()
        count = db.query(ComplianceRule).count()
        print(f"Seeded {count} compliance rules.")
        return count

    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    seed_rules()
