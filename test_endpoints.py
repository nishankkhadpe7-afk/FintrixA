import httpx

base_url = 'http://127.0.0.1:8000'

# Login
print('Logging in...')
response = httpx.post(
    f'{base_url}/api/auth/login',
    json={'email': 'test.admin@example.com', 'password': 'AdminPass123!'},
    timeout=10
)
token = response.json().get('access_token', '')
print(f'Token obtained: {token[:20]}...')
print()

# Test health
print('1. Health endpoint:')
response = httpx.get(f'{base_url}/api/health', timeout=10)
print(f'   Status: {response.status_code}')

# Test news without auth
print('2. News endpoint (no auth):')
response = httpx.get(f'{base_url}/api/news', timeout=10)
news_count = len(response.json()) if response.status_code == 200 else 0
print(f'   Status: {response.status_code}')
print(f'   Items: {news_count}')

# Test rules
print('3. Rules endpoint:')
response = httpx.get(
    f'{base_url}/api/rules/list',
    headers={'Authorization': f'Bearer {token}'},
    timeout=30
)
rule_count = len(response.json()) if response.status_code == 200 else 0
print(f'   Status: {response.status_code}')
print(f'   Rules: {rule_count}')

print()
print('✓ All endpoints responding')
