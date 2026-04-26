import httpx
import json

base_url = 'http://127.0.0.1:8000'

print('Testing login response...')
response = httpx.post(
    f'{base_url}/api/auth/login',
    json={'email': 'test.admin@example.com', 'password': 'AdminPass123!'},
    timeout=10
)
print(f'Status: {response.status_code}')
data = response.json()
print(f'Response: {json.dumps(data, indent=2)}')
print()

if 'token' in data:
    token = data['token']
    print(f'Token: {token[:20]}...')
    
    # Test rules with proper token
    print()
    print('Testing rules endpoint with token...')
    response = httpx.get(
        f'{base_url}/api/rules/list',
        headers={'Authorization': f'Bearer {token}'},
        timeout=30
    )
    print(f'Rules Status: {response.status_code}')
    if response.status_code == 200:
        print(f'Rules Count: {len(response.json())}')
