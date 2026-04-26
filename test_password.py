from backend.database import SessionLocal
from backend.auth.models import User
from backend.auth.utils import hash_password, verify_password

db = SessionLocal()

# Check test user
user = db.query(User).filter(User.email == 'test.admin@example.com').first()
if user:
    print(f'✓ Test user found: {user.email}')
    password_input = 'AdminPass123!'
    
    # Try to verify
    is_valid = verify_password(password_input, user.password)
    print(f'  Password verification result: {is_valid}')
    
    if not is_valid:
        print('  ✗ Password hash mismatch!')
        print(f'    Hash type: {"bcrypt" if user.password.startswith("$2") else "werkzeug/sha"}')
        
        # Solution: re-hash with bcrypt
        print('  Fixing user password...')
        user.password = hash_password(password_input)
        db.commit()
        print('  ✓ Password re-hashed with bcrypt')
    else:
        print('  ✓ Password verification successful')
else:
    print('✗ Test user NOT found')

db.close()
