"""
collect_dataset_pro.py — Production-grade dataset collector
- Real images: Unsplash API (470 images across 8 categories)
- Fake images: Local Stable Diffusion XL via diffusers (50 images, CUDA)
- Resumes from checkpoint, validates quality, saves rich metadata

Run from project root:
    python scripts/collect_dataset_pro.py
"""

import os, sys, json, time, uuid, hashlib, traceback
from pathlib import Path
from datetime import datetime

import requests
from PIL import Image
from tqdm import tqdm
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths & env
# ---------------------------------------------------------------------------
ROOT       = Path(__file__).parent.parent
DATASET    = ROOT / "dataset"
REAL_ROOT  = DATASET / "real"
FAKE_DIR   = DATASET / "fake"
META_DIR   = DATASET / "metadata"
CKPT_FILE  = DATASET / "checkpoint.json"
REPORT     = DATASET / "dataset_report.json"

load_dotenv(ROOT / "backend" / ".env")
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

# ---------------------------------------------------------------------------
# Category definitions
# ---------------------------------------------------------------------------
CATEGORIES = {
    "clean_modern": {
        "target_real": 100, "target_fake": 20,
        "lighting": "bright", "clutter": "none", "angle": "standard",
        "queries": [
            "modern living room interior design",
            "luxury kitchen minimalist",
            "contemporary bedroom white",
            "clean bathroom modern tiles",
            "scandinavian interior design",
        ],
    },
    "cluttered": {
        "target_real": 80, "target_fake": 10,
        "lighting": "mixed", "clutter": "high", "angle": "standard",
        "queries": [
            "messy bedroom clothes floor",
            "cluttered home office papers",
            "untidy living room",
            "dirty kitchen counters",
            "cluttered apartment interior",
        ],
    },
    "poor_lighting": {
        "target_real": 60, "target_fake": 5,
        "lighting": "dark", "clutter": "low", "angle": "standard",
        "queries": [
            "dark room interior night",
            "dimly lit bedroom moody",
            "shadowy hallway interior",
            "low light living room",
            "dark basement interior",
        ],
    },
    "odd_angles": {
        "target_real": 50, "target_fake": 5,
        "lighting": "mixed", "clutter": "low", "angle": "unusual",
        "queries": [
            "wide angle room interior fisheye",
            "partial room view corner",
            "overhead room view interior",
            "room interior close up detail",
            "narrow hallway perspective",
        ],
    },
    "old_outdated": {
        "target_real": 50, "target_fake": 5,
        "lighting": "mixed", "clutter": "medium", "angle": "standard",
        "queries": [
            "old house interior vintage",
            "vintage kitchen 1980s retro",
            "outdated bathroom tiles old",
            "retro living room 70s",
            "old fashioned bedroom decor",
        ],
    },
    "small_cramped": {
        "target_real": 50, "target_fake": 5,
        "lighting": "mixed", "clutter": "medium", "angle": "standard",
        "queries": [
            "tiny apartment studio interior",
            "small bedroom narrow space",
            "compact kitchen small apartment",
            "micro apartment interior",
            "small bathroom tiny",
        ],
    },
    "accessibility": {
        "target_real": 40, "target_fake": 0,
        "lighting": "bright", "clutter": "none", "angle": "standard",
        "queries": [
            "bathroom grab bar accessibility",
            "wheelchair accessible room interior",
            "ramp interior accessible home",
            "wide doorway wheelchair accessible",
            "accessible bathroom walk in shower",
        ],
    },
    "architectural": {
        "target_real": 40, "target_fake": 0,
        "lighting": "bright", "clutter": "none", "angle": "detail",
        "queries": [
            "exposed brick wall interior",
            "hardwood floor detail interior",
            "crown molding ceiling detail",
            "vaulted ceiling interior",
            "architectural detail interior staircase",
        ],
    },
}

# ---------------------------------------------------------------------------
# SDXL fake image prompts (50 total)
# ---------------------------------------------------------------------------
FAKE_PROMPTS = [
    # clean_modern (20)
    ("clean_modern", "photorealistic modern living room, bright natural light, 4k, interior design photography"),
    ("clean_modern", "photorealistic luxury kitchen white cabinets, marble countertop, 4k"),
    ("clean_modern", "photorealistic contemporary master bedroom, minimalist, 4k"),
    ("clean_modern", "photorealistic modern bathroom, walk-in shower, 4k"),
    ("clean_modern", "photorealistic scandinavian living room, wood accents, 4k"),
    ("clean_modern", "photorealistic open plan kitchen dining, 4k, real estate photo"),
    ("clean_modern", "photorealistic penthouse bedroom, floor to ceiling windows, 4k"),
    ("clean_modern", "photorealistic spa bathroom, freestanding tub, 4k"),
    ("clean_modern", "photorealistic home office modern, clean desk, 4k"),
    ("clean_modern", "photorealistic dining room modern chandelier, 4k"),
    ("clean_modern", "photorealistic loft apartment living room, 4k"),
    ("clean_modern", "photorealistic farmhouse kitchen, shaker cabinets, 4k"),
    ("clean_modern", "photorealistic kids bedroom modern, colorful, 4k"),
    ("clean_modern", "photorealistic ensuite bathroom double vanity, 4k"),
    ("clean_modern", "photorealistic sunroom interior, plants, 4k"),
    ("clean_modern", "photorealistic laundry room modern, 4k"),
    ("clean_modern", "photorealistic mudroom entryway, 4k"),
    ("clean_modern", "photorealistic walk-in closet organized, 4k"),
    ("clean_modern", "photorealistic basement home theater, 4k"),
    ("clean_modern", "photorealistic garage converted living space, 4k"),
    # cluttered (10)
    ("cluttered", "photorealistic messy bedroom, clothes on floor, realistic, 4k"),
    ("cluttered", "photorealistic cluttered home office, papers everywhere, realistic, 4k"),
    ("cluttered", "photorealistic untidy living room, realistic clutter, 4k"),
    ("cluttered", "photorealistic busy kitchen counters, lots of items, realistic, 4k"),
    ("cluttered", "photorealistic packed storage room, boxes, realistic, 4k"),
    ("cluttered", "photorealistic teenager bedroom messy, posters, realistic, 4k"),
    ("cluttered", "photorealistic hoarder living room, lots of stuff, realistic, 4k"),
    ("cluttered", "photorealistic workshop garage interior, tools, realistic, 4k"),
    ("cluttered", "photorealistic craft room supplies everywhere, realistic, 4k"),
    ("cluttered", "photorealistic home library books stacked, realistic, 4k"),
    # poor_lighting (5)
    ("poor_lighting", "photorealistic dark bedroom night lamp only, moody, realistic, 4k"),
    ("poor_lighting", "photorealistic dimly lit living room evening, realistic, 4k"),
    ("poor_lighting", "photorealistic shadowy hallway interior, realistic, 4k"),
    ("poor_lighting", "photorealistic basement dark interior, single bulb, realistic, 4k"),
    ("poor_lighting", "photorealistic candlelit dining room, dark, realistic, 4k"),
    # odd_angles (5)
    ("odd_angles", "photorealistic living room wide angle fisheye lens, distorted, realistic, 4k"),
    ("odd_angles", "photorealistic bedroom corner view partial, realistic, 4k"),
    ("odd_angles", "photorealistic kitchen overhead top down view, realistic, 4k"),
    ("odd_angles", "photorealistic bathroom close up detail tiles, realistic, 4k"),
    ("odd_angles", "photorealistic narrow hallway perspective vanishing point, realistic, 4k"),
    # old_outdated (5)
    ("old_outdated", "photorealistic 1970s living room retro decor, realistic, 4k"),
    ("old_outdated", "photorealistic vintage kitchen 1980s appliances, realistic, 4k"),
    ("old_outdated", "photorealistic outdated bathroom pink tiles, realistic, 4k"),
    ("old_outdated", "photorealistic old house interior worn, realistic, 4k"),
    ("old_outdated", "photorealistic retro bedroom wallpaper, realistic, 4k"),
    # small_cramped (5)
    ("small_cramped", "photorealistic tiny studio apartment interior, realistic, 4k"),
    ("small_cramped", "photorealistic small bedroom narrow, realistic, 4k"),
    ("small_cramped", "photorealistic compact galley kitchen, realistic, 4k"),
    ("small_cramped", "photorealistic micro apartment living area, realistic, 4k"),
    ("small_cramped", "photorealistic small bathroom cramped, realistic, 4k"),
]

# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint() -> dict:
    if CKPT_FILE.exists():
        return json.loads(CKPT_FILE.read_text())
    return {"real": {}, "fake": []}


def save_checkpoint(ckpt: dict):
    CKPT_FILE.write_text(json.dumps(ckpt, indent=2))


# ---------------------------------------------------------------------------
# Metadata helper
# ---------------------------------------------------------------------------

def save_meta(filename: str, category: str, img_type: str, source: str, extra: dict):
    cat_cfg = CATEGORIES.get(category, {})
    meta = {
        "filename": filename,
        "category": category,
        "type": img_type,
        "source": source,
        "lighting_condition": extra.pop("lighting_condition", cat_cfg.get("lighting", "unknown")),
        "clutter_level": extra.pop("clutter_level", cat_cfg.get("clutter", "unknown")),
        "angle_type": extra.pop("angle_type", cat_cfg.get("angle", "standard")),
        "accessibility_features": extra.pop("accessibility_features", category == "accessibility"),
        "collected_at": datetime.now().isoformat(),
        **extra,
    }
    (META_DIR / f"{Path(filename).stem}.json").write_text(json.dumps(meta, indent=2))


# ---------------------------------------------------------------------------
# Image quality validator
# ---------------------------------------------------------------------------

def validate_image(path: Path, min_w=500, min_h=400) -> tuple[bool, str]:
    if not path.exists() or path.stat().st_size == 0:
        return False, "zero-byte or missing"
    try:
        with Image.open(path) as img:
            w, h = img.size
            if w < min_w or h < min_h:
                return False, f"too small ({w}x{h})"
        return True, "ok"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Real image collection — Unsplash
# ---------------------------------------------------------------------------

def collect_real_images(ckpt: dict):
    if not UNSPLASH_KEY:
        print("[SKIP] UNSPLASH_ACCESS_KEY not set.")
        return

    print("\n" + "="*60)
    print("PHASE 1: Real Images — Unsplash API")
    print("="*60)

    real_ckpt = ckpt.setdefault("real", {})
    req_count = 0
    RATE_LIMIT = 45          # stay under 50/hr free tier
    HOUR = 3600

    for cat_name, cfg in CATEGORIES.items():
        target = cfg["target_real"]
        if target == 0:
            continue

        cat_dir = REAL_ROOT / cat_name
        cat_dir.mkdir(parents=True, exist_ok=True)

        collected = real_ckpt.get(cat_name, 0)
        existing  = len([f for f in cat_dir.glob("*.jpg") if f.stat().st_size > 0])
        collected  = max(collected, existing)

        if collected >= target:
            print(f"  [{cat_name}] already at {collected}/{target}, skipping.")
            real_ckpt[cat_name] = collected
            continue

        needed  = target - collected
        queries = cfg["queries"]
        per_q   = max(1, -(-needed // len(queries)))   # ceiling div

        print(f"\n  [{cat_name}] need {needed} more (target {target})")

        with tqdm(total=needed, desc=f"  {cat_name}", unit="img") as pbar:
            for query in queries:
                if collected >= target:
                    break
                page = 1
                while collected < target:
                    # Rate-limit guard
                    if req_count >= RATE_LIMIT:
                        wait = HOUR / RATE_LIMIT
                        tqdm.write(f"  [RATE LIMIT] sleeping {wait:.0f}s ...")
                        time.sleep(wait)
                        req_count = 0

                    try:
                        resp = requests.get(
                            "https://api.unsplash.com/search/photos",
                            params={"query": query, "per_page": min(30, per_q), "page": page},
                            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
                            timeout=15,
                        )
                        req_count += 1

                        if resp.status_code == 429:
                            tqdm.write("  [429] Rate limited — sleeping 60s")
                            time.sleep(60)
                            continue
                        resp.raise_for_status()
                    except requests.RequestException as e:
                        tqdm.write(f"  [ERROR] API: {e}")
                        time.sleep(5)
                        break

                    photos = resp.json().get("results", [])
                    if not photos:
                        break

                    for photo in photos:
                        if collected >= target:
                            break
                        img_id   = photo["id"]
                        filename = f"{cat_name}_{img_id}.jpg"
                        dest     = cat_dir / filename

                        if dest.exists() and dest.stat().st_size > 0:
                            collected += 1
                            pbar.update(1)
                            continue

                        try:
                            r = requests.get(photo["urls"]["regular"], timeout=30)
                            r.raise_for_status()
                            dest.write_bytes(r.content)
                        except Exception as e:
                            tqdm.write(f"  [ERROR] download: {e}")
                            continue

                        ok, reason = validate_image(dest)
                        if not ok:
                            dest.unlink(missing_ok=True)
                            tqdm.write(f"  [INVALID] {filename}: {reason}")
                            continue

                        save_meta(filename, cat_name, "real", "unsplash", {
                            "unsplash_id": img_id,
                            "query": query,
                            "photographer": photo.get("user", {}).get("name", ""),
                        })
                        collected += 1
                        pbar.update(1)
                        time.sleep(1)   # 1 req/sec

                    page += 1
                    time.sleep(1)

        real_ckpt[cat_name] = collected
        save_checkpoint(ckpt)
        print(f"  [{cat_name}] final: {collected}/{target}")


# ---------------------------------------------------------------------------
# Fake image generation — Local SDXL (CUDA)
# ---------------------------------------------------------------------------

def load_sdxl_pipeline():
    """Load SDXL with memory optimisations for 6GB VRAM."""
    import torch
    from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

    print("\n  Loading SDXL pipeline (fp16, attention slicing) ...")
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
    )
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()
    pipe = pipe.to("cuda")
    print(f"  SDXL loaded. VRAM used: {torch.cuda.memory_allocated()/1024**3:.2f} GB")
    return pipe


def load_sd15_fallback():
    """SD 1.5 fallback for low-VRAM situations."""
    import torch
    from diffusers import StableDiffusionPipeline

    print("\n  [FALLBACK] Loading SD 1.5 (fp16) ...")
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16,
    )
    pipe.enable_attention_slicing()
    pipe = pipe.to("cuda")
    return pipe


def generate_fake_images(ckpt: dict):
    import torch

    print("\n" + "="*60)
    print("PHASE 2: Fake Images — Local Stable Diffusion (CUDA)")
    print("="*60)

    FAKE_DIR.mkdir(parents=True, exist_ok=True)
    done_set = set(ckpt.get("fake", []))

    remaining = [(i, cat, p) for i, (cat, p) in enumerate(FAKE_PROMPTS)
                 if str(i) not in done_set]

    if not remaining:
        print("  All fake images already generated.")
        return

    print(f"  {len(remaining)} images to generate on {torch.cuda.get_device_name(0)}")
    print(f"  VRAM available: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB")

    pipe = None
    try:
        pipe = load_sdxl_pipeline()
        is_sdxl = True
    except (RuntimeError, Exception) as e:
        print(f"  [WARN] SDXL load failed ({e}), trying SD 1.5 fallback ...")
        try:
            pipe = load_sd15_fallback()
            is_sdxl = False
        except Exception as e2:
            print(f"  [ERROR] Both pipelines failed: {e2}")
            return

    gen_size = (768, 768) if is_sdxl else (512, 512)

    with tqdm(total=len(remaining), desc="  Generating", unit="img") as pbar:
        for idx, cat, prompt in remaining:
            img_id   = str(uuid.uuid4())[:8]
            filename = f"fake_{cat}_{img_id}.jpg"
            dest     = FAKE_DIR / filename

            try:
                torch.cuda.empty_cache()
                vram_before = torch.cuda.memory_allocated() / 1024**3

                result = pipe(
                    prompt=prompt,
                    num_inference_steps=25,
                    width=gen_size[0],
                    height=gen_size[1],
                    guidance_scale=7.5,
                ).images[0]

                result.save(dest, quality=95)
                vram_after = torch.cuda.memory_allocated() / 1024**3

                ok, reason = validate_image(dest)
                if not ok:
                    dest.unlink(missing_ok=True)
                    tqdm.write(f"  [INVALID] {filename}: {reason}")
                    continue

                save_meta(filename, cat, "fake", "stable-diffusion-xl" if is_sdxl else "stable-diffusion-1.5", {
                    "prompt": prompt,
                    "model": "stabilityai/stable-diffusion-xl-base-1.0" if is_sdxl else "runwayml/stable-diffusion-v1-5",
                    "steps": 25,
                    "vram_gb_used": round(vram_after, 2),
                })

                done_set.add(str(idx))
                ckpt["fake"] = list(done_set)
                save_checkpoint(ckpt)
                pbar.set_postfix({"VRAM": f"{vram_after:.1f}GB", "cat": cat})

            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                tqdm.write(f"  [OOM] Skipping {filename} — reduce resolution or free VRAM")
            except Exception as e:
                tqdm.write(f"  [ERROR] {filename}: {e}")
                traceback.print_exc()

            pbar.update(1)
            time.sleep(0.5)

    # Cleanup
    del pipe
    torch.cuda.empty_cache()
    print(f"  Done. VRAM freed: {torch.cuda.memory_allocated()/1024**3:.2f} GB remaining")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Property AI Masterpiece — Production Dataset Collector")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create all dirs
    for cat in CATEGORIES:
        (REAL_ROOT / cat).mkdir(parents=True, exist_ok=True)
    FAKE_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)

    ckpt = load_checkpoint()

    collect_real_images(ckpt)
    generate_fake_images(ckpt)

    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Run `python scripts/verify_dataset.py` for the full report.")
