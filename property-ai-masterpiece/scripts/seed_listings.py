"""Seed realistic demo listings for the buyer dashboard to show."""
import sqlite3, uuid, pathlib, json

DB = pathlib.Path("backend/app/database/property_ai.db")
conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

# Get seller user id
seller = conn.execute(
    "SELECT id FROM users WHERE email='seller1@propertyai.demo'"
).fetchone()
if not seller:
    print("seller1@propertyai.demo not found — run setup_fastapi.py first")
    conn.close()
    exit(1)

seller_id = seller["id"]

LISTINGS = [
    {
        "title": "Modern 3BR Family Home",
        "description": "Modern minimalist home with open-plan living, chef's kitchen and landscaped garden. Bright natural light throughout.",
        "address": "142 Maple Street",
        "city": "Seattle", "state": "WA", "zip_code": "98101",
        "price": 685000, "property_type": "house",
        "bedrooms": 3, "bathrooms": 2.0, "square_feet": 1850,
        "year_built": 2018, "overall_quality_score": 87.5,
        "authenticity_verified": 1,
    },
    {
        "title": "Downtown Studio Apartment",
        "description": "Sleek studio in the heart of downtown. Floor-to-ceiling windows, modern finishes, rooftop access.",
        "address": "88 Urban Ave #12B",
        "city": "Seattle", "state": "WA", "zip_code": "98104",
        "price": 320000, "property_type": "apartment",
        "bedrooms": 1, "bathrooms": 1.0, "square_feet": 620,
        "year_built": 2020, "overall_quality_score": 82.0,
        "authenticity_verified": 1,
    },
    {
        "title": "Luxury 4BR Waterfront Condo",
        "description": "Stunning waterfront condo with panoramic views. Premium finishes, private balcony, concierge service.",
        "address": "1 Harbor View Drive #PH3",
        "city": "Miami", "state": "FL", "zip_code": "33101",
        "price": 1250000, "property_type": "condo",
        "bedrooms": 4, "bathrooms": 3.5, "square_feet": 3200,
        "year_built": 2019, "overall_quality_score": 93.0,
        "authenticity_verified": 1,
    },
    {
        "title": "Cozy 2BR Townhouse",
        "description": "Charming townhouse with private patio, updated kitchen and hardwood floors throughout.",
        "address": "55 Oak Lane",
        "city": "Austin", "state": "TX", "zip_code": "78701",
        "price": 425000, "property_type": "townhouse",
        "bedrooms": 2, "bathrooms": 1.5, "square_feet": 1200,
        "year_built": 2015, "overall_quality_score": 78.0,
        "authenticity_verified": 1,
    },
    {
        "title": "Scandinavian 2BR Apartment",
        "description": "Light-filled apartment with Scandinavian design, white oak floors, and a gourmet kitchen.",
        "address": "300 Nordic Way #4A",
        "city": "Chicago", "state": "IL", "zip_code": "60601",
        "price": 375000, "property_type": "apartment",
        "bedrooms": 2, "bathrooms": 2.0, "square_feet": 980,
        "year_built": 2017, "overall_quality_score": 85.0,
        "authenticity_verified": 1,
    },
    {
        "title": "Rustic 5BR Ranch House",
        "description": "Spacious ranch-style home on half an acre. Exposed beams, stone fireplace, wrap-around porch.",
        "address": "7890 Ranch Road",
        "city": "Denver", "state": "CO", "zip_code": "80201",
        "price": 795000, "property_type": "house",
        "bedrooms": 5, "bathrooms": 3.0, "square_feet": 3400,
        "year_built": 2005, "overall_quality_score": 80.0,
        "authenticity_verified": 1,
    },
    {
        "title": "Industrial Loft Apartment",
        "description": "Raw industrial loft with exposed brick, polished concrete floors and 14ft ceilings.",
        "address": "22 Factory District #7",
        "city": "Chicago", "state": "IL", "zip_code": "60607",
        "price": 290000, "property_type": "apartment",
        "bedrooms": 1, "bathrooms": 1.0, "square_feet": 850,
        "year_built": 2012, "overall_quality_score": 76.0,
        "authenticity_verified": 0,
    },
    {
        "title": "New Build 3BR Smart Home",
        "description": "Brand new smart home with solar panels, EV charging, automated lighting and premium appliances.",
        "address": "9 Innovation Blvd",
        "city": "Austin", "state": "TX", "zip_code": "78702",
        "price": 560000, "property_type": "house",
        "bedrooms": 3, "bathrooms": 2.5, "square_feet": 2100,
        "year_built": 2024, "overall_quality_score": 91.0,
        "authenticity_verified": 1,
    },
    {
        "title": "Affordable 1BR Starter Condo",
        "description": "Perfect starter home. Updated bathroom, new appliances, secure building with gym.",
        "address": "400 Starter St #2C",
        "city": "Phoenix", "state": "AZ", "zip_code": "85001",
        "price": 185000, "property_type": "condo",
        "bedrooms": 1, "bathrooms": 1.0, "square_feet": 550,
        "year_built": 2010, "overall_quality_score": 70.0,
        "authenticity_verified": 1,
    },
    {
        "title": "Classic 4BR Colonial",
        "description": "Timeless colonial with formal dining room, updated kitchen, large backyard and 2-car garage.",
        "address": "18 Heritage Lane",
        "city": "Denver", "state": "CO", "zip_code": "80202",
        "price": 720000, "property_type": "house",
        "bedrooms": 4, "bathrooms": 2.5, "square_feet": 2800,
        "year_built": 1998, "overall_quality_score": 83.0,
        "authenticity_verified": 1,
    },
]

inserted = 0
for l in LISTINGS:
    lid = uuid.uuid4().hex
    conn.execute(
        """INSERT INTO listings
           (id, seller_id, title, description, address, city, state, zip_code,
            price, property_type, bedrooms, bathrooms, square_feet, year_built,
            overall_quality_score, authenticity_verified, status, published_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'published', CURRENT_TIMESTAMP)""",
        (lid, seller_id, l["title"], l["description"], l["address"],
         l["city"], l["state"], l["zip_code"], l["price"], l["property_type"],
         l["bedrooms"], l["bathrooms"], l["square_feet"], l["year_built"],
         l["overall_quality_score"], l["authenticity_verified"]),
    )
    inserted += 1

conn.commit()
conn.close()
print(f"Seeded {inserted} demo listings — all published and ready for buyer search.")
