import sqlite3, pathlib
db = sqlite3.connect("backend/app/database/property_ai.db")
db.row_factory = sqlite3.Row
n = db.execute("SELECT COUNT(*) as n FROM listings WHERE status='published'").fetchone()["n"]
print(f"Published listings: {n}")
rows = db.execute("SELECT title, city, price, overall_quality_score FROM listings WHERE status='published' ORDER BY price").fetchall()
for r in rows:
    print(f"  {r['title']} | {r['city']} | ${r['price']:,.0f} | Q:{r['overall_quality_score']}")
db.close()
