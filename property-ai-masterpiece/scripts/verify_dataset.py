"""
verify_dataset.py — Dataset quality verification & statistics report
Run from project root: python scripts/verify_dataset.py
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from PIL import Image
from tqdm import tqdm

ROOT     = Path(__file__).parent.parent
DATASET  = ROOT / "dataset"
REAL_ROOT = DATASET / "real"
FAKE_DIR  = DATASET / "fake"
META_DIR  = DATASET / "metadata"
REPORT    = DATASET / "dataset_report.json"

CATEGORIES = [
    "clean_modern", "cluttered", "poor_lighting", "odd_angles",
    "old_outdated", "small_cramped", "accessibility", "architectural",
]

TARGETS = {
    "clean_modern":  {"real": 100, "fake": 20},
    "cluttered":     {"real": 80,  "fake": 10},
    "poor_lighting": {"real": 60,  "fake": 5},
    "odd_angles":    {"real": 50,  "fake": 5},
    "old_outdated":  {"real": 50,  "fake": 5},
    "small_cramped": {"real": 50,  "fake": 5},
    "accessibility": {"real": 40,  "fake": 0},
    "architectural": {"real": 40,  "fake": 0},
}

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def scan_images(directory: Path) -> list[Path]:
    return [f for f in directory.glob("*.jpg") if f.stat().st_size > 0] if directory.exists() else []


def check_image(path: Path) -> dict:
    try:
        with Image.open(path) as img:
            w, h = img.size
            mode = img.mode
        return {"valid": True, "width": w, "height": h, "mode": mode,
                "size_kb": round(path.stat().st_size / 1024, 1)}
    except Exception as e:
        return {"valid": False, "error": str(e), "size_kb": 0}


def load_meta(stem: str) -> dict | None:
    p = META_DIR / f"{stem}.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------

def verify():
    report = {
        "generated_at": datetime.now().isoformat(),
        "categories": {},
        "fake": {},
        "totals": {},
        "issues": [],
    }

    total_real = total_fake = total_valid = total_invalid = 0
    total_meta_ok = total_meta_missing = 0

    print("\n" + "="*65)
    print("DATASET VERIFICATION REPORT")
    print("="*65)

    # ── Real images per category ──────────────────────────────────────
    print("\n── Real Images by Category ──────────────────────────────────")

    for cat in CATEGORIES:
        cat_dir = REAL_ROOT / cat
        images  = scan_images(cat_dir)
        target  = TARGETS[cat]["real"]

        stats = defaultdict(int)
        widths, heights, sizes = [], [], []
        zero_byte = invalid = meta_missing = 0

        all_files = list(cat_dir.glob("*.jpg")) if cat_dir.exists() else []
        for f in tqdm(all_files, desc=f"  {cat}", leave=False):
            if f.stat().st_size == 0:
                zero_byte += 1
                report["issues"].append({"file": str(f), "issue": "zero-byte"})
                continue

            info = check_image(f)
            if not info["valid"]:
                invalid += 1
                report["issues"].append({"file": str(f), "issue": info.get("error")})
                continue

            widths.append(info["width"])
            heights.append(info["height"])
            sizes.append(info["size_kb"])

            meta = load_meta(f.stem)
            if meta is None:
                meta_missing += 1
                total_meta_missing += 1
            else:
                total_meta_ok += 1

        valid_count = len(images)
        pct = round(valid_count / target * 100) if target else 0
        icon = PASS if valid_count >= target else (WARN if valid_count >= target * 0.8 else FAIL)

        avg_w = round(sum(widths)/len(widths)) if widths else 0
        avg_h = round(sum(heights)/len(heights)) if heights else 0
        avg_s = round(sum(sizes)/len(sizes), 1) if sizes else 0

        print(f"  [{icon}] {cat:<20} {valid_count:>4}/{target:<4} ({pct}%)"
              f"  avg {avg_w}x{avg_h}  {avg_s}KB/img"
              + (f"  ⚠️  {zero_byte} zero-byte" if zero_byte else "")
              + (f"  ❌ {invalid} corrupt" if invalid else "")
              + (f"  📄 {meta_missing} no-meta" if meta_missing else ""))

        report["categories"][cat] = {
            "valid": valid_count, "target": target, "pct": pct,
            "zero_byte": zero_byte, "invalid": invalid, "meta_missing": meta_missing,
            "avg_width": avg_w, "avg_height": avg_h, "avg_size_kb": avg_s,
        }
        total_real += valid_count
        total_valid += valid_count
        total_invalid += invalid + zero_byte

    # ── Fake images ───────────────────────────────────────────────────
    print("\n── Fake Images ──────────────────────────────────────────────")

    fake_files = list(FAKE_DIR.glob("*.jpg")) if FAKE_DIR.exists() else []
    fake_by_cat = defaultdict(list)
    fake_invalid = fake_zero = fake_meta_missing = 0
    fake_sizes = []

    for f in tqdm(fake_files, desc="  fake", leave=False):
        if f.stat().st_size == 0:
            fake_zero += 1
            continue
        info = check_image(f)
        if not info["valid"]:
            fake_invalid += 1
            continue
        fake_sizes.append(info["size_kb"])

        meta = load_meta(f.stem)
        cat  = meta.get("category", "unknown") if meta else "unknown"
        fake_by_cat[cat].append(f)
        if meta is None:
            fake_meta_missing += 1

    total_fake_target = sum(v["fake"] for v in TARGETS.values())
    total_fake = len(fake_files) - fake_zero - fake_invalid
    pct_fake = round(total_fake / total_fake_target * 100) if total_fake_target else 0
    icon = PASS if total_fake >= total_fake_target else (WARN if total_fake >= total_fake_target * 0.8 else FAIL)

    print(f"  [{icon}] Total fake: {total_fake}/{total_fake_target} ({pct_fake}%)")
    for cat, files in sorted(fake_by_cat.items()):
        t = TARGETS.get(cat, {}).get("fake", "?")
        print(f"       {cat:<20} {len(files):>3} / {t}")

    if fake_zero:   print(f"  {WARN} Zero-byte: {fake_zero}")
    if fake_invalid: print(f"  {FAIL} Corrupt:   {fake_invalid}")

    report["fake"] = {
        "valid": total_fake, "target": total_fake_target, "pct": pct_fake,
        "by_category": {k: len(v) for k, v in fake_by_cat.items()},
        "zero_byte": fake_zero, "invalid": fake_invalid,
        "avg_size_kb": round(sum(fake_sizes)/len(fake_sizes), 1) if fake_sizes else 0,
    }
    total_valid += total_fake
    total_invalid += fake_zero + fake_invalid

    # ── Metadata completeness ─────────────────────────────────────────
    print("\n── Metadata Completeness ────────────────────────────────────")
    all_meta = list(META_DIR.glob("*.json"))
    required_fields = ["filename","category","type","lighting_condition",
                       "clutter_level","angle_type","accessibility_features"]
    incomplete = 0
    for mf in all_meta:
        try:
            m = json.loads(mf.read_text())
            if not all(k in m for k in required_fields):
                incomplete += 1
        except Exception:
            incomplete += 1

    meta_icon = PASS if incomplete == 0 else WARN
    print(f"  [{meta_icon}] Metadata files: {len(all_meta)}  incomplete: {incomplete}")

    # ── Summary ───────────────────────────────────────────────────────
    grand_target = sum(v["real"] + v["fake"] for v in TARGETS.values())
    grand_total  = total_real + total_fake
    pct_grand    = round(grand_total / grand_target * 100) if grand_target else 0

    print("\n" + "="*65)
    print("SUMMARY")
    print("="*65)
    print(f"  Real images  : {total_real} / 470")
    print(f"  Fake images  : {total_fake} / 50")
    print(f"  Grand total  : {grand_total} / {grand_target}  ({pct_grand}%)")
    print(f"  Valid files  : {total_valid}")
    print(f"  Invalid/zero : {total_invalid}")
    print(f"  Metadata     : {len(all_meta)} files  ({incomplete} incomplete)")
    print(f"  Issues logged: {len(report['issues'])}")

    overall_icon = PASS if grand_total >= grand_target * 0.9 else (WARN if grand_total >= grand_target * 0.5 else FAIL)
    print(f"\n  [{overall_icon}] Dataset completeness: {pct_grand}%")

    report["totals"] = {
        "real": total_real, "fake": total_fake,
        "grand_total": grand_total, "grand_target": grand_target,
        "pct_complete": pct_grand, "invalid": total_invalid,
        "metadata_files": len(all_meta), "metadata_incomplete": incomplete,
    }

    REPORT.write_text(json.dumps(report, indent=2))
    print(f"\n  Report saved → {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    verify()
