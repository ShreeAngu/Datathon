import sqlite3
conn = sqlite3.connect('backend/app/database/property_ai.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT COUNT(*) as cnt FROM listings WHERE status='published'")
print("Published listings:", dict(cur.fetchone()))

cur.execute("SELECT id, title, status, price FROM listings WHERE status='published'")
for r in cur.fetchall():
    print(dict(r))

print("\nImages sample:")
cur.execute("SELECT listing_id, image_path, is_primary FROM images LIMIT 10")
for r in cur.fetchall():
    print(dict(r))
