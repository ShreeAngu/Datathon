"""Fix existing image_path entries that store full paths — normalize to filename only."""
import sqlite3, pathlib

db = sqlite3.connect("backend/app/database/property_ai.db")
db.row_factory = sqlite3.Row

images = db.execute("SELECT id, image_path FROM images").fetchall()
fixed = 0
for img in images:
    p = pathlib.Path(img["image_path"])
    # If it's already just a filename, skip
    if str(p) == p.name:
        continue
    db.execute("UPDATE images SET image_path=? WHERE id=?", (p.name, img["id"]))
    print(f"Fixed: {img['image_path']} -> {p.name}")
    fixed += 1

db.commit()
db.close()
print(f"Fixed {fixed} image path(s).")
