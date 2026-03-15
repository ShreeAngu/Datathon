"""
Dataset Collection Script
Downloads real interior images from Unsplash and generates fake ones via
Stable Diffusion XL on Hugging Face Inference API.
"""

import os
import json
import time
import uuid
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

DATASET_ROOT = Path(__file__).parent.parent / "dataset"
REAL_DIR = DATASET_ROOT / "real"
FAKE_DIR = DATASET_ROOT / "fake"
META_DIR = DATASET_ROOT / "metadata"

for d in (REAL_DIR, FAKE_DIR, META_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Unsplash: 10 images per room type × 5 types = 50 total
ROOM_QUERIES = ["living room interior", "kitchen interior", "bedroom interior",
                "bathroom interior", "staircase interior"]
IMAGES_PER_QUERY = 10

# SDXL: 4 prompts × 5 types = 20 total
FAKE_PROMPTS = [
    "photorealistic modern living room, 8k, interior design",
    "photorealistic luxury kitchen, 8k, interior design",
    "photorealistic cozy bedroom, 8k, interior design",
    "photorealistic spa bathroom, 8k, interior design",
    "photorealistic elegant staircase, 8k, interior design",
]
FAKE_PER_PROMPT = 4  # 5 × 4 = 20

SDXL_API_URL = (
    "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_metadata(filename: str, label: str, source: str, extra: dict) -> None:
    meta = {
        "filename": filename,
        "label": label,
        "source": source,
        "collected_at": datetime.utcnow().isoformat(),
        **extra,
    }
    meta_path = META_DIR / f"{Path(filename).stem}.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def download_file(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)
        return True
    except requests.RequestException as e:
        print(f"  [ERROR] Failed to download {url}: {e}")
        return False


# ---------------------------------------------------------------------------
# Real images — Unsplash
# ---------------------------------------------------------------------------

def collect_real_images() -> None:
    if not UNSPLASH_ACCESS_KEY:
        print("[SKIP] UNSPLASH_ACCESS_KEY not set. Skipping real image collection.")
        return

    print("\n=== Collecting REAL images from Unsplash ===")
    total = 0

    for query in ROOM_QUERIES:
        print(f"\n  Query: '{query}'")
        page = 1
        collected = 0

        while collected < IMAGES_PER_QUERY:
            try:
                resp = requests.get(
                    "https://api.unsplash.com/search/photos",
                    params={
                        "query": query,
                        "per_page": min(IMAGES_PER_QUERY - collected, 30),
                        "page": page,
                        "orientation": "landscape",
                    },
                    headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                    timeout=15,
                )
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"  [ERROR] Unsplash API error: {e}")
                break

            results = resp.json().get("results", [])
            if not results:
                print("  [WARN] No more results.")
                break

            for photo in results:
                if collected >= IMAGES_PER_QUERY:
                    break

                img_url = photo["urls"]["regular"]
                img_id = photo["id"]
                filename = f"real_{img_id}.jpg"
                dest = REAL_DIR / filename

                if dest.exists():
                    print(f"  [SKIP] {filename} already exists.")
                    collected += 1
                    continue

                print(f"  Downloading {filename} ...", end=" ")
                ok = download_file(img_url, dest)
                if ok:
                    save_metadata(
                        filename=filename,
                        label="real",
                        source="unsplash",
                        extra={
                            "unsplash_id": img_id,
                            "query": query,
                            "photographer": photo.get("user", {}).get("name", ""),
                            "unsplash_url": photo.get("links", {}).get("html", ""),
                        },
                    )
                    collected += 1
                    total += 1
                    print("OK")

                # Unsplash free tier: 50 req/hr — be polite
                time.sleep(0.5)

            page += 1
            time.sleep(1)

        print(f"  Collected {collected}/{IMAGES_PER_QUERY} for '{query}'")

    print(f"\n[DONE] Real images collected: {total}")


# ---------------------------------------------------------------------------
# Fake images — Stable Diffusion XL via HF Inference API
# ---------------------------------------------------------------------------

def generate_fake_images() -> None:
    if not HF_TOKEN:
        print("[SKIP] HF_TOKEN not set. Skipping fake image generation.")
        return

    print("\n=== Generating FAKE images via SDXL (HF Inference API) ===")
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    total = 0

    for prompt in FAKE_PROMPTS:
        print(f"\n  Prompt: '{prompt}'")

        for i in range(FAKE_PER_PROMPT):
            img_id = str(uuid.uuid4())[:8]
            filename = f"fake_{img_id}.jpg"
            dest = FAKE_DIR / filename

            print(f"  Generating {filename} ({i + 1}/{FAKE_PER_PROMPT}) ...", end=" ")

            # HF Inference API may return 503 while model loads — retry up to 3×
            for attempt in range(3):
                try:
                    resp = requests.post(
                        SDXL_API_URL,
                        headers=headers,
                        json={"inputs": prompt, "parameters": {"num_inference_steps": 30}},
                        timeout=120,
                    )

                    if resp.status_code == 503:
                        wait = int(resp.headers.get("Retry-After", 20))
                        print(f"model loading, waiting {wait}s ...", end=" ")
                        time.sleep(wait)
                        continue

                    resp.raise_for_status()

                    with open(dest, "wb") as f:
                        f.write(resp.content)

                    save_metadata(
                        filename=filename,
                        label="fake",
                        source="stable-diffusion-xl",
                        extra={"prompt": prompt, "model": "stabilityai/stable-diffusion-xl-base-1.0"},
                    )
                    total += 1
                    print("OK")
                    break

                except requests.RequestException as e:
                    print(f"\n  [ERROR] Attempt {attempt + 1}/3 failed: {e}")
                    time.sleep(5)
            else:
                print("  [FAIL] Skipping after 3 failed attempts.")

            # Respect HF rate limits
            time.sleep(3)

        time.sleep(2)

    print(f"\n[DONE] Fake images generated: {total}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Property AI Masterpiece — Dataset Collection")
    print("=" * 50)
    collect_real_images()
    generate_fake_images()
    print("\nAll done. Check dataset/real, dataset/fake, and dataset/metadata.")
