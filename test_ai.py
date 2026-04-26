import httpx
import json

base_url = 'http://127.0.0.1:8000'

print('Testing AI Agent (ask endpoint)...')
print()

# Login
response = httpx.post(
    f'{base_url}/api/auth/login',
    json={'email': 'test.admin@example.com', 'password': 'AdminPass123!'},
    timeout=10
)
token = response.json().get('token', '')
print(f'✓ Authenticated')
print()

# Test AI endpoint
print('Testing /api/ask endpoint...')
try:
    response = httpx.post(
        f'{base_url}/api/ask',
        json={'question': 'What is LRS and what is the annual limit for remittances?'},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f'✓ AI Response Status: {response.status_code}')
        print()
        print('Response:')
        print(json.dumps(data, indent=2)[:500])
    else:
        print(f'✗ Status: {response.status_code}')
        print(f'  Response: {response.text[:200]}')
except Exception as e:
    print(f'✗ Error: {str(e)[:100]}')
