#!/usr/bin/env python3
"""Verify SEBI rules were persisted to the database."""

from backend.database import SessionLocal
from backend.rules.models import ComplianceRule

db = SessionLocal()
try:
    total = db.query(ComplianceRule).count()
    sebi_count = db.query(ComplianceRule).filter(ComplianceRule.regulator == 'SEBI').count()
    
    print(f"Total rules in database: {total}")
    print(f"SEBI rules: {sebi_count}")
    
    if sebi_count > 0:
        print("\nFirst 5 SEBI rules:")
        sebi_rules = db.query(ComplianceRule).filter(ComplianceRule.regulator == 'SEBI').limit(5).all()
        for rule in sebi_rules:
            print(f"  - {rule.rule_id}: {rule.title}")
            print(f"    Domain: {rule.domain}, Type: {rule.type}, Severity: {rule.severity}")
finally:
    db.close()
