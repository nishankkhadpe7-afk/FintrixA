"""
Seed additional test data for robust testing.
Adds test users, what-if sessions, messages, and rule evaluations.
"""

import json
from datetime import datetime, timezone, timedelta
from backend.database import SessionLocal
from backend.auth.models import User, WhatIfSession, Message
from backend.rules.models import RuleEvaluation
from backend.models import News
from backend.auth.utils import hash_password

def seed_test_users():
    """Add test users to the database."""
    db = SessionLocal()
    
    try:
        # Check if test users already exist
        existing_count = db.query(User).filter(User.email.like("test%@example.com")).count()
        
        if existing_count > 0:
            print(f"Test users already exist ({existing_count}). Skipping user seed.")
            return
        
        test_users = [
            {"email": "test.user1@example.com", "password": "TestPass123!"},
            {"email": "test.user2@example.com", "password": "TestPass123!"},
            {"email": "test.user3@example.com", "password": "TestPass123!"},
            {"email": "test.forex@example.com", "password": "TestPass123!"},
            {"email": "test.lending@example.com", "password": "TestPass123!"},
            {"email": "test.trading@example.com", "password": "TestPass123!"},
            {"email": "test.admin@example.com", "password": "AdminPass123!"},
            {"email": "test.auditor@example.com", "password": "AuditPass123!"},
        ]
        
        created_count = 0
        for user_data in test_users:
            # Check if user already exists
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                user = User(
                    email=user_data["email"],
                    password=hash_password(user_data["password"])
                )
                db.add(user)
                created_count += 1
        
        db.commit()
        print(f"Seeded {created_count} test users.")
        
    except Exception as e:
        db.rollback()
        print(f"User seed error: {e}")
    finally:
        db.close()


def seed_test_sessions():
    """Add test what-if sessions."""
    db = SessionLocal()
    
    try:
        # Get or create test users
        test_users = db.query(User).filter(User.email.like("test%@example.com")).all()
        
        if not test_users:
            print("No test users found. Run seed_test_users first.")
            return
        
        # Check existing sessions
        existing_sessions = db.query(WhatIfSession).count()
        if existing_sessions > 5:
            print(f"Sessions already exist ({existing_sessions}). Skipping session seed.")
            return
        
        created_count = 0
        for user in test_users[:3]:  # Use first 3 test users
            # Create 2 sessions per user
            for i in range(2):
                session = WhatIfSession(
                    user_id=user.id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=i)
                )
                db.add(session)
                created_count += 1
        
        db.commit()
        print(f"Seeded {created_count} test what-if sessions.")
        
    except Exception as e:
        db.rollback()
        print(f"Session seed error: {e}")
    finally:
        db.close()


def seed_test_messages():
    """Add test messages to sessions."""
    db = SessionLocal()
    
    try:
        sessions = db.query(WhatIfSession).all()
        
        if not sessions:
            print("No sessions found. Run seed_test_sessions first.")
            return
        
        # Check existing messages
        existing_messages = db.query(Message).count()
        if existing_messages > 10:
            print(f"Messages already exist ({existing_messages}). Skipping message seed.")
            return
        
        message_pairs = [
            {
                "user": "Can I transfer $200,000 to the US under LRS?",
                "assistant": "No, the LRS limit is USD 250,000 per financial year. Your proposed transfer would exceed regulations. Consider splitting across fiscal years."
            },
            {
                "user": "What are the TCS implications for ₹15 lakhs foreign transfer?",
                "assistant": "For ₹15 lakhs, TCS of 5% applies (capped at benefit of credit). With valid documents, you may reduce to 0% or 1% depending on your tax profile."
            },
            {
                "user": "Is an NPA after 30 days overdue?",
                "assistant": "No. Per RBI IRAC norms, an account is classified as NPA only after 90 days of non-payment. 30 days would still be in 'standard' category."
            },
            {
                "user": "Can bonds be held indefinitely?",
                "assistant": "Bond holding duration depends on the specific bond terms and issuer regulations. Government securities typically have fixed maturity dates."
            },
            {
                "user": "What triggers a compliance audit?",
                "assistant": "Compliance audits are triggered by rule violations, high-risk transactions, regulator requests, or scheduled periodic audits."
            },
        ]
        
        created_count = 0
        for session in sessions:
            for pair in message_pairs[:2]:  # Add 2 message pairs per session
                # User message
                user_msg = Message(
                    session_id=session.id,
                    role="user",
                    content=pair["user"],
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=5)
                )
                db.add(user_msg)
                created_count += 1
                
                # Assistant message
                assistant_msg = Message(
                    session_id=session.id,
                    role="assistant",
                    content=pair["assistant"],
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=4)
                )
                db.add(assistant_msg)
                created_count += 1
        
        db.commit()
        print(f"Seeded {created_count} test messages.")
        
    except Exception as e:
        db.rollback()
        print(f"Message seed error: {e}")
    finally:
        db.close()


def seed_test_rule_evaluations():
    """Add audit trail of rule evaluations."""
    db = SessionLocal()
    
    try:
        # Get test users and rules
        test_users = db.query(User).filter(User.email.like("test%@example.com")).all()
        from backend.rules.models import ComplianceRule
        rules = db.query(ComplianceRule).limit(5).all()
        
        if not test_users or not rules:
            print("Not enough test users or rules. Run other seeds first.")
            return
        
        # Check existing evaluations
        existing_evals = db.query(RuleEvaluation).count()
        if existing_evals > 20:
            print(f"Rule evaluations already exist ({existing_evals}). Skipping evaluation seed.")
            return
        
        test_inputs = [
            {"domain": "forex", "amount": 200000, "declared": True},
            {"domain": "forex", "amount": 3000000, "declared": False},
            {"domain": "lending", "days_overdue": 45, "loan_amount": 500000},
            {"domain": "lending", "days_overdue": 95, "loan_amount": 1000000},
            {"domain": "trading", "leverage": 5, "position_size": 1000000},
            {"domain": "bonds", "maturity_days": 365, "rating": "AAA"},
        ]
        
        created_count = 0
        for user in test_users[:3]:
            for rule in rules:
                for input_data in test_inputs[:2]:
                    evaluation = RuleEvaluation(
                        user_id=user.id,
                        rule_id=rule.rule_id,
                        input_summary=json.dumps(input_data),
                        matched=(user.id % 2 == 0),  # Alternate matched/not matched
                        trace=json.dumps({"evaluated": True, "timestamp": datetime.now(timezone.utc).isoformat()}),
                        source="whatif",
                        created_at=datetime.now(timezone.utc) - timedelta(hours=user.id)
                    )
                    db.add(evaluation)
                    created_count += 1
        
        db.commit()
        print(f"Seeded {created_count} rule evaluations.")
        
    except Exception as e:
        db.rollback()
        print(f"Rule evaluation seed error: {e}")
    finally:
        db.close()


def seed_test_news():
    """Add sample news articles."""
    db = SessionLocal()
    
    try:
        # Check existing news
        existing_news = db.query(News).count()
        if existing_news > 5:
            print(f"News articles already exist ({existing_news}). Skipping news seed.")
            return
        
        test_news = [
            {
                "title": "RBI Updates LRS Guidelines for 2024",
                "description": "RBI has issued revised guidelines for the Liberalised Remittance Scheme.",
                "content": "The RBI announced updates to the LRS, increasing the limit to $250,000 for FY 2024-25.",
                "source": "RBI Official",
                "url": "https://rbi.org.in/lrs-update-2024"
            },
            {
                "title": "SEBI Tightens Trading Margin Requirements",
                "description": "New margin requirements effective from April 1, 2024.",
                "content": "SEBI has mandated higher margin requirements to reduce leverage and systemic risk.",
                "source": "SEBI Notice",
                "url": "https://sebi.gov.in/margin-update-2024"
            },
            {
                "title": "Income Tax on NRI Investment Income Changes",
                "description": "Tax rate changes for NRI foreign investments effective immediately.",
                "content": "The government has revised tax treatment on certain NRI investments from April 2024.",
                "source": "IT Ministry",
                "url": "https://incometax.gov.in/nri-tax-2024"
            },
            {
                "title": "Banking Sector Stress Test Results Released",
                "description": "RBI releases annual stress test results for scheduled banks.",
                "content": "Latest stress tests show banking sector still resilient despite economic headwinds.",
                "source": "RBI Bulletin",
                "url": "https://rbi.org.in/stress-test-2024"
            },
            {
                "title": "New AML Compliance Framework Announced",
                "description": "Stricter anti-money laundering requirements from May 2024.",
                "content": "Financial institutions must implement enhanced KYC and transaction monitoring by May 31, 2024.",
                "source": "FIU India",
                "url": "https://fiu.gov.in/aml-framework-2024"
            },
        ]
        
        created_count = 0
        for news_data in test_news:
            existing = db.query(News).filter(News.title == news_data["title"]).first()
            if not existing:
                news = News(
                    title=news_data["title"],
                    description=news_data["description"],
                    content=news_data["content"],
                    source=news_data["source"],
                    url=news_data["url"],
                    published_at=datetime.now(timezone.utc) - timedelta(days=1)
                )
                db.add(news)
                created_count += 1
        
        db.commit()
        print(f"Seeded {created_count} news articles.")
        
    except Exception as e:
        db.rollback()
        print(f"News seed error: {e}")
    finally:
        db.close()


def seed_all():
    """Run all seed functions."""
    print("Starting database seeding...")
    seed_test_users()
    seed_test_sessions()
    seed_test_messages()
    seed_test_rule_evaluations()
    seed_test_news()
    print("Database seeding completed!")


if __name__ == "__main__":
    seed_all()
