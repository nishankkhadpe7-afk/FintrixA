import httpx
import json

# Test frontend API communication
base_url = 'http://127.0.0.1:8000'

print('Frontend to Backend API Tests:')
print()

# 1. Test login endpoint
print('1. Testing login endpoint...')
try:
    response = httpx.post(
        f'{base_url}/api/auth/login',
        json={'email': 'test.admin@example.com', 'password': 'AdminPass123!'},
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print('   ✓ Login successful')
        print(f'     Token type: {data.get("token_type", "N/A")}')
        token = data.get('access_token', '')
    else:
        print(f'   ✗ Login failed: {response.status_code}')
        token = None
except Exception as e:
    print(f'   ✗ Error: {str(e)[:60]}')
    token = None

print()

# 2. Test authenticated endpoint
if token:
    print('2. Testing authenticated news endpoint...')
    try:
        response = httpx.get(
            f'{base_url}/api/news',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print('   ✓ Protected endpoint accessible')
            print(f'     Got {len(data)} news items')
        else:
            print(f'   ✗ Failed: {response.status_code}')
    except Exception as e:
        print(f'   ✗ Error: {str(e)[:60]}')

print()
print('3. Testing Mistral AI endpoint...')
try:
    response = httpx.post(
        f'{base_url}/api/ai-agent/ask',
        json={'question': 'Is LRS limit 250000 USD?', 'context': 'Compliance'},
        headers={'Authorization': f'Bearer {token}'} if token else {},
        timeout=10
    )
    if response.status_code == 200:
        print('   ✓ AI agent working')
    else:
        print(f'   ℹ Status: {response.status_code}')
except Exception as e:
    print(f'   ℹ Error: {str(e)[:50]}')
