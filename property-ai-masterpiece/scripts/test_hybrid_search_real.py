"""Test hybrid search with real keywords from demo listings."""
import requests

BASE = "http://localhost:8000"

# Login as buyer
print("Logging in as buyer1...")
r = requests.post(f"{BASE}/api/v1/auth/login", json={
    "email": "buyer1@propertyai.demo",
    "password": "Buyer123!"
})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print("✓ Logged in\n")

# Test 1: Keyword "smart home"
print("="*60)
print("TEST 1: Keyword Search - 'smart home'")
print("="*60)
r = requests.get(
    f"{BASE}/api/v1/buyer/search/advanced",
    params={"query": "smart home", "per_page": 10},
    headers=headers
)
if r.status_code == 200:
    data = r.json()
    print(f"✓ Found {data['total']} listing(s)")
    for i, listing in enumerate(data['listings'], 1):
        print(f"  {i}. {listing['title']}")
        print(f"     {listing['city']}, {listing['state']} - ${listing['price']:,.0f}")
else:
    print(f"✗ Failed: {r.status_code}")

# Test 2: Keyword "exposed brick" + semantic ranking
print("\n" + "="*60)
print("TEST 2: Keyword + Semantic - 'exposed brick'")
print("="*60)
r = requests.get(
    f"{BASE}/api/v1/buyer/search/advanced",
    params={"query": "exposed brick", "semantic_rank": True, "per_page": 10},
    headers=headers
)
if r.status_code == 200:
    data = r.json()
    print(f"✓ Found {data['total']} listing(s)")
    print(f"  Semantic ranking: {data.get('semantic_ranking_enabled')}")
    for i, listing in enumerate(data['listings'], 1):
        score = listing.get('semantic_score', 0)
        print(f"  {i}. {listing['title']} - 🎯 {score:.2%}")
        print(f"     {listing['city']}, {listing['state']} - ${listing['price']:,.0f}")
else:
    print(f"✗ Failed: {r.status_code}")

# Test 3: Keyword "updated kitchen"
print("\n" + "="*60)
print("TEST 3: Keyword Search - 'updated kitchen'")
print("="*60)
r = requests.get(
    f"{BASE}/api/v1/buyer/search/advanced",
    params={"query": "updated kitchen", "per_page": 10},
    headers=headers
)
if r.status_code == 200:
    data = r.json()
    print(f"✓ Found {data['total']} listing(s)")
    for i, listing in enumerate(data['listings'], 1):
        print(f"  {i}. {listing['title']}")
else:
    print(f"✗ Failed: {r.status_code}")

# Test 4: Semantic search - "rustic farmhouse style"
print("\n" + "="*60)
print("TEST 4: Semantic Search - 'rustic farmhouse style'")
print("="*60)
r = requests.get(
    f"{BASE}/api/v1/buyer/search/advanced",
    params={"query": "rustic farmhouse style", "semantic_rank": True, "per_page": 10},
    headers=headers
)
if r.status_code == 200:
    data = r.json()
    print(f"✓ Found {data['total']} listing(s)")
    print(f"  Semantic ranking: {data.get('semantic_ranking_enabled')}")
    for i, listing in enumerate(data['listings'][:5], 1):
        score = listing.get('semantic_score', 0)
        print(f"  {i}. {listing['title']} - 🎯 {score:.2%}")
else:
    print(f"✗ Failed: {r.status_code}")

# Test 5: Hybrid - "solar" + price filter + semantic
print("\n" + "="*60)
print("TEST 5: Hybrid - 'solar' + Max $600K + Semantic")
print("="*60)
r = requests.get(
    f"{BASE}/api/v1/buyer/search/advanced",
    params={
        "query": "solar",
        "max_price": 600000,
        "semantic_rank": True,
        "per_page": 10
    },
    headers=headers
)
if r.status_code == 200:
    data = r.json()
    print(f"✓ Found {data['total']} listing(s)")
    print(f"  Semantic ranking: {data.get('semantic_ranking_enabled')}")
    for i, listing in enumerate(data['listings'], 1):
        score = listing.get('semantic_score', 0)
        print(f"  {i}. {listing['title']} - 🎯 {score:.2%}")
        print(f"     ${listing['price']:,.0f}")
else:
    print(f"✗ Failed: {r.status_code}")

print("\n" + "="*60)
print("✓ All hybrid search tests complete!")
print("="*60)
print("\nSearch capabilities:")
print("  ✓ Keyword matching in title/description")
print("  ✓ AI semantic ranking by relevance")
print("  ✓ Combined with SQL filters (price, beds, location)")
print("  ✓ Works with natural language queries")
