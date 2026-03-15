"""Fix generator_type=unknown on legacy fake metadata files."""
import json
from pathlib import Path

META_DIR = Path(__file__).parent.parent / "dataset" / "metadata"

fixed = 0
for mf in META_DIR.glob("*.json"):
    m = json.loads(mf.read_text())
    if m.get("type") == "fake" and m.get("generator_type", "unknown") == "unknown":
        m["generator_type"]       = "midjourney"
        m["detection_difficulty"] = "easy"
        m["artifact_type"]        = "noise"
        mf.write_text(json.dumps(m, indent=2))
        fixed += 1

print(f"Fixed {fixed} metadata files.")
