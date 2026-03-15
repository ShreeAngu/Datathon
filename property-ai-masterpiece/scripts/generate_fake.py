"""
generate_fake.py — Fake image generator with Replicate SDXL + public URL fallback.
Run from project root: python scripts/generate_fake.py
"""

import os
import json
import time
import uuid
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
FAKE_DIR = Path(__file__).parent.parent / "dataset" / "fake"
META_DIR = Path(__file__).parent.parent / "dataset" / "metadata"
FAKE_DIR.mkdir(parents=True, exist_ok=True)
META_DIR.mkdir(parents=True, exist_ok=True)

TARGET = 20

PROMPTS = [
    "photorealistic modern living room, natural light, 8k, interior design",
    "photorealistic luxury kitchen with island, 8k, interior design",
    "photorealistic cozy master bedroom, warm lighting, 8k, interior design",
    "photorealistic spa bathroom with marble tiles, 8k, interior design",
    "photorealistic elegant wooden staircase, 8k, interior design",
    "photorealistic open plan living room, minimalist, 8k",
    "photorealistic scandinavian kitchen, white cabinets, 8k",
    "photorealistic bohemian bedroom, plants, 8k",
    "photorealistic modern bathroom, freestanding tub, 8k",
    "photorealistic grand staircase, chandelier, 8k",
    "photorealistic industrial loft living room, 8k",
    "photorealistic farmhouse kitchen, wooden beams, 8k",
    "photorealistic kids bedroom, colorful, 8k",
    "photorealistic ensuite bathroom, double vanity, 8k",
    "photorealistic spiral staircase, contemporary, 8k",
    "photorealistic penthouse living room, city view, 8k",
    "photorealistic chef kitchen, stainless steel, 8k",
    "photorealistic luxury master bedroom, velvet, 8k",
    "photorealistic outdoor shower bathroom, 8k",
    "photorealistic floating staircase, glass railing, 8k",
]

# Fallback: Unsplash source URLs (no API key needed)
FALLBACK_URLS = [
    "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800",
    "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800",
    "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800",
    "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=800",
    "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
    "https://images.unsplash.com/photo-1567767292278-a4f21aa2d36e?w=800",
    "https://images.unsplash.com/photo-1565183997392-2f6f122e5912?w=800",
    "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
    "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=800",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800",
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800",
    "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=800",
    "https://images.unsplash.com/photo-1600566752355-35792bedcfea?w=800",
    "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800",
    "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=800",
    "https://images.unsplash.com/photo-1600210492493-0946911123ea?w=800",
    "https://images.unsplash.com/photo-1600121848594-d8644e57abab?w=800",
    "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=800",
    "https://images.unsplash.com/photo-1600573472592-401b489a3cdc?w=800",
]


def save_metadata(filename, source, extra):
    meta = {
        "filename": filename,
        "label": "fake",
        "source": source,
        "collected_at": datetime.now().isoformat(),
        **extra,
    }
    with open(META_DIR / f"{Path(filename).stem}.json", "w") as f:
        json.dump(meta, f, indent=2)


def download_url(url, dest):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def generate_via_replicate(prompt, dest):
    """Call Replicate SDXL and poll until image is ready."""
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    # SDXL on Replicate
    payload = {
        "version": "7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd46c929f9bdc",
        "input": {"prompt": prompt, "num_inference_steps": 25, "width": 768, "height": 768},
    }
    try:
        r = requests.post("https://api.replicate.com/v1/predictions",
                          json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        prediction_id = r.json()["id"]
    except Exception as e:
        print(f"  [ERROR] Replicate submit failed: {e}")
        return False

    # Poll for result (max 90s)
    for _ in range(30):
        time.sleep(3)
        try:
            poll = requests.get(f"https://api.replicate.com/v1/predictions/{prediction_id}",
                                headers=headers, timeout=15)
            poll.raise_for_status()
            data = poll.json()
            status = data.get("status")
            if status == "succeeded":
                img_url = data["output"][0]
                return download_url(img_url, dest)
            elif status in ("failed", "canceled"):
                print(f"  [ERROR] Replicate prediction {status}")
                return False
        except Exception as e:
            print(f"  [ERROR] Polling error: {e}")
    print("  [ERROR] Replicate timed out after 90s")
    return False


def collect_fake_images():
    existing = [f for f in FAKE_DIR.iterdir()
                if f.suffix == ".jpg" and f.name != ".gitkeep"]
    already = len(existing)
    print(f"\n  Already have {already} fake images.")
    needed = max(0, TARGET - already)
    if needed == 0:
        print("  Target already met. Nothing to do.")
        return

    use_replicate = bool(REPLICATE_API_TOKEN)
    total = 0

    for i in range(needed):
        img_id = str(uuid.uuid4())[:8]
        filename = f"fake_{img_id}.jpg"
        dest = FAKE_DIR / filename
        prompt = PROMPTS[i % len(PROMPTS)]

        print(f"\n  [{i+1}/{needed}] Generating {filename}")

        ok = False
        source = "unknown"

        # --- Try Replicate first ---
        if use_replicate:
            print(f"  Trying Replicate SDXL ...", end=" ", flush=True)
            ok = generate_via_replicate(prompt, dest)
            if ok:
                source = "replicate-sdxl"
                print("OK")

        # --- Fallback: direct Unsplash image URL ---
        if not ok:
            fallback_url = FALLBACK_URLS[i % len(FALLBACK_URLS)]
            print(f"  Falling back to public URL ...", end=" ", flush=True)
            ok = download_url(fallback_url, dest)
            if ok:
                source = "unsplash-fallback"
                print("OK")

        if ok:
            save_metadata(filename, source, {"prompt": prompt})
            total += 1
        else:
            print(f"  [FAIL] Could not obtain image {i+1}, skipping.")

        time.sleep(1)

    print(f"\n[DONE] Fake images collected this run: {total}")
    print(f"[DONE] Total fake images in dataset: {already + total}")


if __name__ == "__main__":
    print("=== Fake Image Generator ===")
    collect_fake_images()
