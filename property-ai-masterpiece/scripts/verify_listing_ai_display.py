"""Verify AI detection display in My Listings section."""
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Login as seller
print("🔐 Logging in as seller...")
login_resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "seller1@propertyai.demo",
    "password": "Seller123!"
})

token = login_resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Get listings
print("\n📋 Fetching listings...")
listings_resp = requests.get(f"{BASE_URL}/seller/listings", headers=headers)
listings_data = listings_resp.json()
listings = listings_data.get("listings", []) if isinstance(listings_data, dict) else listings_data

if not listings:
    print("❌ No listings found")
    exit(1)

print(f"✅ Found {len(listings)} listing(s)\n")

# Show each listing with AI detection status
for listing in listings[:3]:  # Show first 3
    print("=" * 70)
    print(f"🏠 {listing['title']}")
    print(f"   ${listing.get('price', 0):,.0f} - {listing['status']}")
    print(f"   Quality Score: {listing.get('overall_quality_score', 'N/A')}")
    print(f"   Authenticity: {'✅ Verified' if listing.get('authenticity_verified') else '⚠️  Contains AI'}")
    
    # Get analysis for this listing
    analysis_resp = requests.get(f"{BASE_URL}/seller/listings/{listing['id']}/analysis", 
                                 headers=headers)
    
    if analysis_resp.status_code == 200:
        analysis_data = analysis_resp.json()
        analyses = analysis_data.get("analyses", [])
        
        if analyses:
            print(f"\n   📸 Images ({len(analyses)}):")
            for item in analyses:
                img = item.get("image", {})
                analysis = item.get("analysis", {})
                
                if analysis:
                    filename = img.get("original_filename", "Unknown")[:30]
                    is_ai = analysis.get("is_ai_generated") == 1
                    ai_prob = analysis.get("ai_probability", 0)
                    
                    # Apply 70% confidence threshold
                    show_confidence = max(ai_prob, 100 - ai_prob) >= 70
                    
                    if is_ai:
                        if show_confidence:
                            status = f"🤖 AI Generated ({ai_prob:.0f}%)"
                        else:
                            status = "❓ Uncertain"
                    else:
                        if show_confidence:
                            status = f"✅ Real ({100-ai_prob:.0f}%)"
                        else:
                            status = "❓ Uncertain"
                    
                    print(f"      • {filename} - {status}")
        else:
            print("\n   📸 No images with analysis data")
    else:
        print(f"\n   ⚠️  Could not fetch analysis: {analysis_resp.status_code}")
    
    print()

print("=" * 70)
print("\n✅ Verification complete!")
print("\n💡 This is what sellers will see in the 'My Listings' tab")
