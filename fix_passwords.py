from backend.database import SessionLocal
from backend.auth.models import User
from backend.auth.utils import hash_password

db = SessionLocal()

test_user_passwords = {
    "test.user1@example.com": "TestPass123!",
    "test.user2@example.com": "TestPass123!",
    "test.user3@example.com": "TestPass123!",
    "test.forex@example.com": "TestPass123!",
    "test.lending@example.com": "TestPass123!",
    "test.trading@example.com": "TestPass123!",
    "test.admin@example.com": "AdminPass123!",
    "test.auditor@example.com": "AuditPass123!",
}

print("Fixing test user passwords...")
fixed_count = 0

for email, password in test_user_passwords.items():
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.password = hash_password(password)
        fixed_count += 1

db.commit()
print(f"✓ Fixed {fixed_count} test user passwords (bcrypt hashing)")
db.close()
