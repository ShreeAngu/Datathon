"""Test hybrid search: SQL filters + keyword matching + semantic ranking."""
import requests
import json

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

# Test 1: Keyword search only
print("="*60)
print("TEST 1: Keyword Search (no semantic ranking)")
print("="*60)
print("Query: 'modern kitchen'")
r = requests.get(
    f"{BASE}/api/v1/buyer/search/advanced",
    params={"query": "modern kitchen", "per_page": 5},
    headers=headers
)
if r.status_code == 200:
    data = r.json()
    print(f"✓ Found {data['total']} listings")
    print(f"  Semantic ranking: {data.get('semantic_ranking_enabled')}")
    for i, listing in enumerate(data['listings'][:3], 1):
        print(f"  {i}. {listing['title']} - ${listing['price']:,.0f}")
        if listing.get('semantic_score'):
            print(f"     Relevance: {listing['semantic_score']:.2%}")
else:
    print(f"✗ Failed: {r.status_code}")

# Test 2: Keyword search + semantic ranking
print("\n" + "="*60)
print("TEST 2: Keyword Search + Semantic Ranking")
print("="*60)
print("Query: 'cozy family home'")
r = requests.get(
    f"{BASE}/api/v1/buyer/search/advanced",
    params={"query": "cozy family home", "semantic_rank": True, "per_page": 5},
    headers=headers
)
if r.status_code == 200:
    data = r.json()
    print(f"✓ Found {data['total']} listings")
    print(f"  Semantic ranking: {data.get('semantic_ranking_enabled')}")
    for i, listing in enumerate(data['listings'][:3], 1):
        print(f"  {i}. {listing['title']} - ${listing['price']:,.0f}")
        if listing.get('semantic_score'):
            print(f"     🎯 Relevance: {listing['semantic_score']:.2%}")
else:
    print(f"✗ Failed: {r.status_code}")

# Test 3: Hybrid - keyword + filters + semantic
print("\n" + "="*60)
print("TEST 3: Hybrid Search (keyword + filters + semantic)")
print("="*60)
print("Query: 'waterfront' + City: Seattle + Max Price: $1M")
r = requests.get(
    f"{BASE}/api/v1/buyer/search/advanced",
    params={
        "query": "waterfront",
        "city": "Seattle",
        "max_price": 1000000,
        "semantic_rank": True,
        "per_page": 5
    },
    headers=headers
)
if r.status_code == 200:
    data = r.json()
    print(f"✓ Found {data['total']} listings")
    print(f"  Semantic ranking: {data.get('semantic_ranking_enabled')}")
    for i, listing in enumerate(data['listings'][:3], 1):
        print(f"  {i}. {listing['title']}")
        print(f"     {listing['city']}, {listing['state']} - ${listing['price']:,.0f}")
        if listing.get('semantic_score'):
            print(f"     🎯 Relevance: {listing['semantic_score']:.2%}")
else:
    print(f"✗ Failed: {r.status_code}")

# Test 4: Filters only (no keyword)
print("\n" + "="*60)
print("TEST 4: Filters Only (no keyword search)")
print("="*60)
print("Filters: Min 3 beds + Max $800K")
r = requests.get(
    f"{BASE}/api/v1/buyer/search/advanced",
    params={
        "min_beds": 3,
        "max_price": 800000,
        "per_page": 5
    },
    headers=headers
)
if r.status_code == 200:
    data = r.json()
    print(f"✓ Found {data['total']} listings")
    print(f"  Semantic ranking: {data.get('semantic_ranking_enabled')}")
    for i, listing in enumerate(data['listings'][:3], 1):
        print(f"  {i}. {listing['title']}")
        print(f"     {listing['bedrooms']} beds - ${listing['price']:,.0f}")
else:
    print(f"✗ Failed: {r.status_code}")

print("\n" + "="*60)
print("✓ Hybrid search tests complete!")
print("="*60)
print("\nFeatures tested:")
print("  ✓ Keyword search in title/description")
print("  ✓ Semantic ranking with CLIP embeddings")
print("  ✓ Hybrid: keyword + SQL filters + semantic")
print("  ✓ SQL filters only (traditional search)")
