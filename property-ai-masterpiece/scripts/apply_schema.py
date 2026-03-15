import sqlite3, pathlib

db = pathlib.Path("backend/app/database/property_ai.db")
schema = pathlib.Path("backend/app/database/schema.sql").read_text()
conn = sqlite3.connect(str(db))
conn.executescript(schema)
conn.commit()
conn.close()
print("Schema applied OK")

conn2 = sqlite3.connect(str(db))
cur = conn2.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print([r[0] for r in cur.fetchall()])
conn2.close()
