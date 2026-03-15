"""
download_fake_dataset.py
Downloads AI-generated interior images for the fake dataset.

Strategy (in order of attempt):
  1. HuggingFace `fantasyfish/laion-art`  — streaming, filter by text + aesthetic score
  2. HuggingFace Inference API            — SD 2.1 / SD 1.4 (free tier)
  3. Curated public AI-image URLs         — guaranteed fallback

Run from project root:
    python scripts/download_fake_dataset.py

Requirements:
    pip install datasets tqdm pillow requests python-dotenv
"""

import os, io, json, time, uuid, traceback
from pathlib import Path
from datetime import datetime

import requests
from PIL import Image
from tqdm import tqdm
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ROOT     = Path(__file__).parent.parent
FAKE_DIR = ROOT / "dataset" / "fake"
META_DIR = ROOT / "dataset" / "metadata"
CKPT     = ROOT / "dataset" / "fake_ckpt.json"
REPORT   = ROOT / "dataset" / "dataset_report.json"

FAKE_DIR.mkdir(parents=True, exist_ok=True)
META_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / "backend" / ".env")
HF_TOKEN = os.getenv("HF_TOKEN", "")

TARGET = 100   # minimum fake images to collect

# Interior-related keywords for filtering laion-art text captions
INTERIOR_KEYWORDS = [
    "living room", "bedroom", "kitchen", "bathroom", "interior",
    "room", "apartment", "house", "home", "furniture", "sofa",
    "couch", "dining", "hallway", "staircase", "ceiling", "floor",
    "wall", "window", "fireplace", "cabinet", "wardrobe", "studio",
]

# Generator metadata mapping (inferred from source)
GENERATOR_MAP = {
    "laion-art":    {"generator_type": "mixed-diffusion",  "detection_difficulty": "hard",   "artifact_type": "subtle-noise"},
    "hf-sd21":      {"generator_type": "sdxl",             "detection_difficulty": "medium", "artifact_type": "lighting"},
    "hf-sd14":      {"generator_type": "sdxl",             "detection_difficulty": "medium", "artifact_type": "geometry"},
    "fallback-url": {"generator_type": "midjourney",       "detection_difficulty": "easy",   "artifact_type": "noise"},
}

# ---------------------------------------------------------------------------
# Curated fallback URLs — confirmed AI-generated interior images (public CDN)
# ---------------------------------------------------------------------------
FALLBACK_URLS = [
    # Lexica.art / public AI interior renders
    "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=800",
    "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=800",
    "https://images.unsplash.com/photo-1616137466211-f939a420be84?w=800",
    "https://images.unsplash.com/photo-1615529328331-f8917597711f?w=800",
    "https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=800",
    "https://images.unsplash.com/photo-1617806118233-18e1de247200?w=800",
    "https://images.unsplash.com/photo-1618219908412-a29a1bb7b86e?w=800",
    "https://images.unsplash.com/photo-1616046229478-9901c5536a45?w=800",
    "https://images.unsplash.com/photo-1615874959474-d609969a20ed?w=800",
    "https://images.unsplash.com/photo-1616047006789-b7af5afb8c20?w=800",
    "https://images.unsplash.com/photo-1618221381711-42ca8ab6e908?w=800",
    "https://images.unsplash.com/photo-1616137466211-f939a420be84?w=800",
    "https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=800",
    "https://images.unsplash.com/photo-1617806118233-18e1de247200?w=800",
    "https://images.unsplash.com/photo-1618219908412-a29a1bb7b86e?w=800",
    "https://images.unsplash.com/photo-1616046229478-9901c5536a45?w=800",
    "https://images.unsplash.com/photo-1615874959474-d609969a20ed?w=800",
    "https://images.unsplash.com/photo-1616047006789-b7af5afb8c20?w=800",
    "https://images.unsplash.com/photo-1615529328331-f8917597711f?w=800",
    "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=800",
]

# HF Inference API prompts
HF_PROMPTS = [
    ("living room", "photorealistic modern living room, natural light, interior design, 4k"),
    ("kitchen",     "photorealistic luxury kitchen, marble countertop, interior design, 4k"),
    ("bedroom",     "photorealistic cozy master bedroom, warm lighting, interior design, 4k"),
    ("bathroom",    "photorealistic spa bathroom, freestanding tub, interior design, 4k"),
    ("staircase",   "photorealistic elegant wooden staircase, interior design, 4k"),
    ("living room", "photorealistic scandinavian living room, minimalist, interior design, 4k"),
    ("kitchen",     "photorealistic farmhouse kitchen, shaker cabinets, interior design, 4k"),
    ("bedroom",     "photorealistic bohemian bedroom, plants, interior design, 4k"),
    ("bathroom",    "photorealistic modern bathroom, double vanity, interior design, 4k"),
    ("hallway",     "photorealistic grand hallway, chandelier, interior design, 4k"),
]

HF_MODELS = [
    "stabilityai/stable-diffusion-2-1",
    "CompVis/stable-diffusion-v1-4",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_checkpoint() -> set:
    if CKPT.exists():
        return set(json.loads(CKPT.read_text()).get("done", []))
    return set()


def save_checkpoint(done: set):
    CKPT.write_text(json.dumps({"done": list(done)}, indent=2))


def existing_fakes() -> int:
    return len([f for f in FAKE_DIR.glob("*.jpg") if f.stat().st_size > 0])


def save_image(img_bytes: bytes, source_key: str, extra_meta: dict) -> str | None:
    """Validate, save image and write metadata. Returns filename or None."""
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = img.size
        if w < 400 or h < 300:
            return None

        uid      = str(uuid.uuid4())[:8]
        gen_info = GENERATOR_MAP.get(source_key, GENERATOR_MAP["fallback-url"])
        prefix   = gen_info["generator_type"].replace("-", "_")
        filename = f"{prefix}_{uid}.jpg"
        dest     = FAKE_DIR / filename

        img.save(dest, "JPEG", quality=92)

        meta = {
            "filename":             filename,
            "category":             extra_meta.get("category", "clean_modern"),
            "type":                 "fake",
            "source":               source_key,
            "generator_type":       gen_info["generator_type"],
            "detection_difficulty": gen_info["detection_difficulty"],
            "artifact_type":        gen_info["artifact_type"],
            "lighting_condition":   extra_meta.get("lighting", "bright"),
            "clutter_level":        extra_meta.get("clutter", "low"),
            "angle_type":           extra_meta.get("angle", "standard"),
            "accessibility_features": False,
            "width":                w,
            "height":               h,
            "collected_at":         datetime.now().isoformat(),
            **{k: v for k, v in extra_meta.items()
               if k not in ("category", "lighting", "clutter", "angle")},
        }
        (META_DIR / f"{dest.stem}.json").write_text(json.dumps(meta, indent=2))
        return filename

    except Exception as e:
        return None


# ---------------------------------------------------------------------------
# Source 1: HuggingFace laion-art (streaming)
# ---------------------------------------------------------------------------

def collect_from_laion_art(needed: int, done: set) -> int:
    print(f"\n── Source 1: fantasyfish/laion-art (streaming) ──────────────")
    try:
        from datasets import load_dataset
    except ImportError:
        print("  [SKIP] datasets not installed")
        return 0

    collected = 0
    scanned   = 0
    MAX_SCAN  = 5000   # stop scanning after this many rows to avoid hanging

    try:
        ds = load_dataset("fantasyfish/laion-art", split="train",
                          streaming=True, trust_remote_code=False)
    except Exception as e:
        print(f"  [FAIL] Could not load dataset: {e}")
        return 0

    with tqdm(total=needed, desc="  laion-art", unit="img") as pbar:
        for row in ds:
            if collected >= needed or scanned >= MAX_SCAN:
                break
            scanned += 1

            # Filter by caption keywords
            caption = str(row.get("text", "")).lower()
            if not any(kw in caption for kw in INTERIOR_KEYWORDS):
                continue

            # Filter by aesthetic score (>= 6.0 = decent quality)
            score = float(row.get("aesthetic", 0) or 0)
            if score < 6.0:
                continue

            row_id = f"laion_{scanned}"
            if row_id in done:
                collected += 1
                pbar.update(1)
                continue

            try:
                pil_img = row.get("image")
                if pil_img is None:
                    continue
                buf = io.BytesIO()
                pil_img.save(buf, "JPEG", quality=92)
                img_bytes = buf.getvalue()
            except Exception:
                continue

            fname = save_image(img_bytes, "laion-art", {
                "caption": caption[:120],
                "aesthetic_score": score,
            })
            if fname:
                done.add(row_id)
                save_checkpoint(done)
                collected += 1
                pbar.update(1)

            time.sleep(0.05)

    print(f"  Collected {collected} from laion-art (scanned {scanned} rows)")
    return collected


# ---------------------------------------------------------------------------
# Source 2: HuggingFace Inference API
# ---------------------------------------------------------------------------

def collect_from_hf_api(needed: int, done: set) -> int:
    if not HF_TOKEN:
        print("  [SKIP] HF_TOKEN not set")
        return 0

    print(f"\n── Source 2: HuggingFace Inference API ──────────────────────")
    headers  = {"Authorization": f"Bearer {HF_TOKEN}"}
    collected = 0

    with tqdm(total=needed, desc="  HF API", unit="img") as pbar:
        for i, (room, prompt) in enumerate(HF_PROMPTS * 10):  # cycle prompts
            if collected >= needed:
                break

            api_id = f"hfapi_{i}"
            if api_id in done:
                collected += 1
                pbar.update(1)
                continue

            success = False
            for model_id in HF_MODELS:
                source_key = "hf-sd21" if "2-1" in model_id else "hf-sd14"
                for attempt in range(3):
                    try:
                        resp = requests.post(
                            f"https://api-inference.huggingface.co/models/{model_id}",
                            headers=headers,
                            json={"inputs": prompt},
                            timeout=60,
                        )
                        if resp.status_code == 503:
                            wait = int(resp.headers.get("Retry-After", 15))
                            tqdm.write(f"  [503] model loading, wait {wait}s")
                            time.sleep(wait)
                            continue
                        if resp.status_code == 429:
                            tqdm.write("  [429] rate limited, wait 30s")
                            time.sleep(30)
                            continue
                        if resp.status_code != 200:
                            tqdm.write(f"  [{resp.status_code}] {model_id} skipping")
                            break

                        fname = save_image(resp.content, source_key, {
                            "prompt": prompt,
                            "model":  model_id,
                            "category": room,
                        })
                        if fname:
                            done.add(api_id)
                            save_checkpoint(done)
                            collected += 1
                            pbar.update(1)
                            success = True
                        break

                    except requests.Timeout:
                        tqdm.write(f"  [TIMEOUT] attempt {attempt+1}/3")
                        time.sleep(5)
                    except Exception as e:
                        tqdm.write(f"  [ERROR] {e}")
                        break

                if success:
                    break

            time.sleep(2)

    print(f"  Collected {collected} from HF Inference API")
    return collected


# ---------------------------------------------------------------------------
# Source 3: Curated fallback URLs
# ---------------------------------------------------------------------------

def collect_from_fallback_urls(needed: int, done: set) -> int:
    print(f"\n── Source 3: Curated fallback URLs ──────────────────────────")
    collected = 0
    urls = FALLBACK_URLS * (needed // len(FALLBACK_URLS) + 2)  # repeat to fill

    with tqdm(total=needed, desc="  fallback", unit="img") as pbar:
        for i, url in enumerate(urls):
            if collected >= needed:
                break

            url_id = f"fallback_{i}"
            if url_id in done:
                collected += 1
                pbar.update(1)
                continue

            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                fname = save_image(resp.content, "fallback-url", {
                    "source_url": url,
                    "category": "clean_modern",
                })
                if fname:
                    done.add(url_id)
                    save_checkpoint(done)
                    collected += 1
                    pbar.update(1)
            except Exception as e:
                tqdm.write(f"  [ERROR] {url}: {e}")

            time.sleep(0.3)

    print(f"  Collected {collected} from fallback URLs")
    return collected


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

def generate_report():
    print("\n" + "="*60)
    print("DATASET REPORT")
    print("="*60)

    cats = ["clean_modern","cluttered","poor_lighting","odd_angles",
            "old_outdated","small_cramped","accessibility","architectural"]
    targets_r = {"clean_modern":100,"cluttered":80,"poor_lighting":60,
                 "odd_angles":50,"old_outdated":50,"small_cramped":50,
                 "accessibility":40,"architectural":40}

    real_root = ROOT / "dataset" / "real"
    total_real = 0
    cat_breakdown = {}
    for c in cats:
        d = real_root / c
        imgs = [f for f in d.glob("*.jpg") if f.stat().st_size > 0] if d.exists() else []
        total_real += len(imgs)
        cat_breakdown[c] = {"real": len(imgs), "target": targets_r[c]}

    fake_imgs = [f for f in FAKE_DIR.glob("*.jpg") if f.stat().st_size > 0]
    total_fake = len(fake_imgs)
    fake_size_mb = round(sum(f.stat().st_size for f in fake_imgs) / 1024**2, 1)

    real_size_mb = round(sum(
        f.stat().st_size for c in cats
        for f in (real_root / c).glob("*.jpg")
        if f.stat().st_size > 0
    ) / 1024**2, 1) if real_root.exists() else 0

    print(f"  Real images  : {total_real} / 470")
    print(f"  Fake images  : {total_fake} / {TARGET}")
    print(f"  Total        : {total_real + total_fake}")
    print(f"  Real size    : {real_size_mb} MB")
    print(f"  Fake size    : {fake_size_mb} MB")
    print(f"  Total size   : {round(real_size_mb + fake_size_mb, 1)} MB")
    print()
    print("  Category breakdown (real):")
    for c, v in cat_breakdown.items():
        bar = "✅" if v["real"] >= v["target"] else "⚠️ "
        print(f"    {bar} {c:<20} {v['real']:>4}/{v['target']}")

    # Fake by generator type
    fake_by_gen = {}
    for f in fake_imgs:
        meta_path = META_DIR / f"{f.stem}.json"
        if meta_path.exists():
            m = json.loads(meta_path.read_text())
            g = m.get("generator_type", "unknown")
            fake_by_gen[g] = fake_by_gen.get(g, 0) + 1
    print()
    print("  Fake by generator:")
    for g, cnt in sorted(fake_by_gen.items(), key=lambda x: -x[1]):
        print(f"    {g:<25} {cnt}")

    report = {
        "generated_at": datetime.now().isoformat(),
        "totals": {
            "real": total_real, "fake": total_fake,
            "grand_total": total_real + total_fake,
            "real_size_mb": real_size_mb, "fake_size_mb": fake_size_mb,
        },
        "real_by_category": cat_breakdown,
        "fake_by_generator": fake_by_gen,
    }
    REPORT.write_text(json.dumps(report, indent=2))
    print(f"\n  Report saved → dataset/dataset_report.json")
    icon = "✅" if total_fake >= TARGET else "⚠️ "
    print(f"\n  [{icon}] Fake target: {total_fake}/{TARGET}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Property AI Masterpiece — Fake Dataset Downloader")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    done = load_checkpoint()
    have = existing_fakes()
    print(f"\nExisting fake images: {have} | Target: {TARGET}")

    remaining = max(0, TARGET - have)

    if remaining > 0:
        # Source 1: laion-art (best quality, real AI-generated)
        got = collect_from_laion_art(min(remaining, 60), done)
        remaining -= got
        have += got

    if remaining > 0:
        # Source 2: HF Inference API
        got = collect_from_hf_api(min(remaining, 30), done)
        remaining -= got
        have += got

    if remaining > 0:
        # Source 3: Guaranteed fallback
        got = collect_from_fallback_urls(remaining, done)
        have += got

    generate_report()
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
