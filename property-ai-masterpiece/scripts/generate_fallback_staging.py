"""
Generate pre-styled fallback images for the Virtual Staging demo.
Picks the best-scoring real images per category and applies style filters.
Run once: python scripts/generate_fallback_staging.py
"""
import sys, os, json
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

ROOT       = Path(__file__).parent.parent
RESULTS    = ROOT / "dataset" / "analysis_results"
STAGED_DIR = ROOT / "dataset" / "staged"
STAGED_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)

STYLE_FILTERS = {
    "modern":       dict(brightness=1.15, color=0.88, contrast=1.10, sharp=1.30),
    "scandinavian": dict(brightness=1.28, color=0.72, contrast=0.92, sharp=1.10),
    "industrial":   dict(brightness=0.88, color=0.48, contrast=1.32, sharp=1.20),
    "rustic":       dict(brightness=1.08, color=1.22, contrast=1.08, sharp=1.10),
    "luxury":       dict(brightness=1.12, color=1.28, contrast=1.28, sharp=1.40),
}

# Pick best images per source category for staging demos
SOURCE_CATEGORIES = ["clean_modern", "small_cramped", "cluttered", "old_outdated"]

def pick_best_images(n=5):
    """Pick top-n real images by quality score."""
    scored = []
    for f in RESULTS.glob("*_analysis.json"):
        try:
            d = json.loads(f.read_text())
            if d.get("authenticity", {}).get("ground_truth_label") != "real":
                continue
            img_path = Path(d.get("image_path", ""))
            if not img_path.exists():
                continue
            cat = img_path.parent.name
            if cat not in SOURCE_CATEGORIES:
                continue
            score = d.get("quality", {}).get("overall_score", 0)
            scored.append((score, img_path, cat))
        except Exception:
            continue
    scored.sort(reverse=True)
    return scored[:n]

def apply_style(img: Image.Image, style: str) -> Image.Image:
    p = STYLE_FILTERS[style]
    img = ImageEnhance.Brightness(img).enhance(p["brightness"])
    img = ImageEnhance.Color(img).enhance(p["color"])
    img = ImageEnhance.Contrast(img).enhance(p["contrast"])
    img = ImageEnhance.Sharpness(img).enhance(p["sharp"])
    if style == "scandinavian":
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4))
    return img

def main():
    best = pick_best_images(5)
    print(f"Selected {len(best)} source images")

    for style in STYLE_FILTERS:
        # Use the top-scoring image as the fallback base for each style
        _, img_path, cat = best[0]
        img      = Image.open(img_path).convert("RGB")
        styled   = apply_style(img, style)
        out_path = STAGED_DIR / f"fallback_{style}.jpg"
        styled.save(str(out_path), "JPEG", quality=95)
        print(f"  ✅ fallback_{style}.jpg  (source: {img_path.name})")

    # Also pre-generate all 5 source images × 5 styles for the gallery
    print("\nPre-generating sample stagings...")
    for score, img_path, cat in best:
        img = Image.open(img_path).convert("RGB")
        for style in STYLE_FILTERS:
            styled   = apply_style(img, style)
            out_path = STAGED_DIR / f"{img_path.stem}_{style}.jpg"
            if not out_path.exists():
                styled.save(str(out_path), "JPEG", quality=95)
        print(f"  ✅ {img_path.stem} — all 5 styles")

    total = len(list(STAGED_DIR.glob("*.jpg")))
    print(f"\n🎨 Done. {total} staged images in dataset/staged/")

if __name__ == "__main__":
    main()
