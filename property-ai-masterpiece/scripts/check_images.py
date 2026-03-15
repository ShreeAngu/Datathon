import sqlite3, pathlib

db = sqlite3.connect("backend/app/database/property_ai.db")
db.row_factory = sqlite3.Row

# Check images table
imgs = db.execute("""
    SELECT i.id, i.listing_id, i.image_path, i.original_filename, i.is_primary,
           l.title, l.status
    FROM images i JOIN listings l ON l.id = i.listing_id
    ORDER BY i.created_at DESC LIMIT 20
""").fetchall()

print(f"Total images in DB: {len(imgs)}")
for r in imgs:
    p = pathlib.Path(r["image_path"])
    exists = p.exists()
    print(f"  [{r['title'][:30]}] {r['original_filename']} | exists={exists} | path={r['image_path']}")

db.close()
