"""Attach existing upload files to seeded demo listings so buyer can see images."""
import sqlite3, uuid, pathlib, random

DB = pathlib.Path("backend/app/database/property_ai.db")
UPLOADS = pathlib.Path("dataset/uploads")

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

# Get all published seeded listings that have no images
listings = conn.execute("""
    SELECT l.id, l.title FROM listings l
    WHERE l.status='published'
    AND NOT EXISTS (SELECT 1 FROM images i WHERE i.listing_id = l.id)
    ORDER BY l.created_at DESC
""").fetchall()

# Get available upload files (clean filenames, no spaces preferred)
all_files = [f for f in UPLOADS.iterdir()
             if f.suffix.lower() in ('.jpg', '.jpeg', '.png')
             and 'enhanced' not in f.name
             and 'fake' not in f.name]

# Pick files without spaces first for cleaner URLs
clean_files = [f for f in all_files if ' ' not in f.name]
if len(clean_files) < 5:
    clean_files = all_files  # fallback

random.seed(42)
random.shuffle(clean_files)

inserted = 0
for i, listing in enumerate(listings):
    # Assign 1-3 images per listing
    count = random.randint(1, 3)
    batch = clean_files[(i * 3) % len(clean_files): (i * 3) % len(clean_files) + count]
    if not batch:
        batch = clean_files[:1]

    for j, f in enumerate(batch):
        iid = uuid.uuid4().hex
        conn.execute(
            """INSERT INTO images(id, listing_id, image_path, original_filename,
               upload_order, is_primary) VALUES (?,?,?,?,?,?)""",
            (iid, listing["id"], f.name, f.name, j, 1 if j == 0 else 0),
        )
        inserted += 1

    print(f"  {listing['title']}: {len(batch)} image(s)")

conn.commit()
conn.close()
print(f"\nAttached {inserted} images to {len(listings)} listings.")
