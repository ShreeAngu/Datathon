"""
process_dataset.py — Batch analysis pipeline for all 570 images.

- Runs CLIP + YOLO + Depth + Authenticity on every image
- Saves per-image JSON to /dataset/analysis_results/
- Indexes embeddings to Pinecone
- Saves depth maps, heatmaps, bounding boxes to /dataset/visualizations/
- Checkpoint/resume support
- Logs to logs/analysis.log

Run from project root:
    python scripts/process_dataset.py
"""

import os, sys, json, time, logging, traceback
from pathlib import Path
from datetime import datetime

import torch
from tqdm import tqdm
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT        = Path(__file__).parent.parent
DATASET     = ROOT / "dataset"
RESULTS_DIR = DATASET / "analysis_results"
LOGS_DIR    = ROOT / "logs"
CKPT_FILE   = DATASET / "pipeline_checkpoint.json"
REPORT_FILE = DATASET / "pinecone_index_status.json"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / "backend" / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "analysis.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("process_dataset")

# ---------------------------------------------------------------------------
# Add backend to path
# ---------------------------------------------------------------------------
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)   # ensure relative imports resolve from project root

# ---------------------------------------------------------------------------
# Collect all images
# ---------------------------------------------------------------------------

def collect_images() -> list[tuple[Path, str]]:
    """Returns list of (image_path, dataset_label) tuples."""
    images = []
    real_root = DATASET / "real"
    fake_dir  = DATASET / "fake"

    for cat_dir in sorted(real_root.iterdir()):
        if cat_dir.is_dir():
            for img in sorted(cat_dir.glob("*.jpg")):
                if img.stat().st_size > 0:
                    images.append((img, "real"))

    for img in sorted(fake_dir.glob("*.jpg")):
        if img.stat().st_size > 0:
            images.append((img, "fake"))

    return images

# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint() -> set:
    if CKPT_FILE.exists():
        return set(json.loads(CKPT_FILE.read_text()).get("done", []))
    return set()


def save_checkpoint(done: set):
    CKPT_FILE.write_text(json.dumps({"done": list(done),
                                      "updated": datetime.now().isoformat()},
                                     indent=2))


# ---------------------------------------------------------------------------
# Per-image processor
# ---------------------------------------------------------------------------

def process_image(img_path: Path, label: str, analyzer, indexer_fn,
                  viz: bool = True) -> dict | None:
    """
    Run full pipeline on one image.
    Returns result dict or None on failure.
    """
    try:
        result = analyzer.analyze(str(img_path), dataset_label=label)

        # Save analysis JSON
        stem        = img_path.stem
        result_path = RESULTS_DIR / f"{stem}_analysis.json"
        save_result = {k: v for k, v in result.items() if k != "embedding"}
        result_path.write_text(json.dumps(save_result, indent=2))

        # Visualizations
        if viz:
            try:
                from app.utils.visualizations import (
                    save_depth_map, save_clutter_heatmap, save_bbox_visualization
                )
                from app.models.depth_model     import estimate_depth
                from app.models.detection_model import detect_objects

                depth_arr, _ = estimate_depth(str(img_path))
                det_result   = detect_objects(str(img_path))

                save_depth_map(stem, depth_arr)
                save_clutter_heatmap(stem, str(img_path), det_result)
                save_bbox_visualization(stem, str(img_path), det_result)
            except Exception as viz_err:
                log.warning(f"Viz failed for {stem}: {viz_err}")

        # Pinecone upsert
        meta = {
            "filename":       img_path.name,
            "label":          label,
            "category":       str(img_path.parent.name),
            "room_type":      result["spatial"].get("room_type", ""),
            "style":          result["spatial"].get("style", ""),
            "overall_score":  result["quality"].get("overall_score", 0),
            "is_ai_generated": result["authenticity"].get("is_ai_generated", False),
            "trust_score":    result["authenticity"].get("trust_score", 0),
            "accessibility_score": result["accessibility"].get("accessibility_score", 0),
        }
        indexer_fn(str(img_path.stem), result["embedding"], meta)

        return result

    except Exception as e:
        log.error(f"Failed {img_path.name}: {e}\n{traceback.format_exc()}")
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("Property AI Masterpiece — Batch Analysis Pipeline")
    log.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

    images = collect_images()
    log.info(f"Total images found: {len(images)}")

    done = load_checkpoint()
    remaining = [(p, l) for p, l in images if p.stem not in done]
    log.info(f"Already processed: {len(done)} | Remaining: {len(remaining)}")

    if not remaining:
        log.info("All images already processed. Generating report...")
    else:
        # Load pipeline
        from app.services.analysis_pipeline import get_analyzer
        from app.services.vector_indexer    import index_image

        analyzer = get_analyzer()
        log.info("Models loaded. Starting batch processing...")

        stats = {"success": 0, "failed": 0, "times": []}

        with tqdm(total=len(remaining), desc="Processing", unit="img") as pbar:
            for img_path, label in remaining:
                result = process_image(img_path, label, analyzer, index_image)

                if result:
                    stats["success"] += 1
                    stats["times"].append(result["processing_time_s"])
                    done.add(img_path.stem)
                    save_checkpoint(done)
                    pbar.set_postfix({
                        "ok": stats["success"],
                        "fail": stats["failed"],
                        "t": f"{result['processing_time_s']:.1f}s",
                        "VRAM": f"{torch.cuda.memory_allocated()/1024**3:.1f}GB"
                              if torch.cuda.is_available() else "CPU",
                    })
                else:
                    stats["failed"] += 1

                pbar.update(1)

                # Periodic VRAM cleanup
                if stats["success"] % 20 == 0 and torch.cuda.is_available():
                    torch.cuda.empty_cache()

        avg_time = round(sum(stats["times"]) / len(stats["times"]), 2) if stats["times"] else 0
        log.info(f"Processed: {stats['success']} OK, {stats['failed']} failed")
        log.info(f"Avg processing time: {avg_time}s/image")

    # --- Final report ---
    from app.services.vector_indexer import get_index_stats

    raw_stats = get_index_stats()
    try:
        # IndexDescription is not directly JSON-serializable; use default=str to coerce
        index_stats = json.loads(json.dumps(raw_stats, default=str))
    except Exception:
        index_stats = {"total_vector_count": "see Pinecone console"}
    total_done  = len(load_checkpoint())

    report = {
        "generated_at":        datetime.now().isoformat(),
        "total_images":        len(images),
        "total_processed":     total_done,
        "success_rate":        round(total_done / max(len(images), 1) * 100, 1),
        "pinecone_index":      index_stats,
        "results_dir":         str(RESULTS_DIR),
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2))

    log.info("=" * 60)
    log.info("FINAL REPORT")
    log.info(f"  Total images      : {len(images)}")
    log.info(f"  Processed         : {total_done}")
    log.info(f"  Success rate      : {report['success_rate']}%")
    pc_count = index_stats.get('total_vector_count', 'N/A') if isinstance(index_stats, dict) else str(index_stats)
    log.info(f"  Pinecone vectors  : {pc_count}")
    log.info(f"  Report saved      : {REPORT_FILE}")
    log.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
