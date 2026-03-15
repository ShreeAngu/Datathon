"""
verify_setup.py — Segment 1 QA Verification Script
Run from the project root: python backend/verify_setup.py
"""

import os
import sys
import ast
from pathlib import Path

# Resolve project root (one level up from this file's directory)
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# Load .env manually so we don't depend on dotenv being installed yet
def load_env(env_path: Path) -> dict:
    env = {}
    if not env_path.exists():
        return env
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


ENV = load_env(BACKEND_DIR / ".env")

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []


def report(label: str, ok: bool, detail: str = "") -> None:
    icon = PASS if ok else FAIL
    msg = f"[{icon}] {label}: {'OK' if ok else 'FAILED'}"
    if detail:
        msg += f" ({detail})"
    results.append((ok, msg))
    print(msg)


# ---------------------------------------------------------------------------
# 1. File Structure
# ---------------------------------------------------------------------------
print("\n── Check 1: File Structure ──────────────────────────────")

required_dirs = [
    PROJECT_ROOT / "backend",
    PROJECT_ROOT / "frontend",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "dataset",
    PROJECT_ROOT / "dataset" / "real",
    PROJECT_ROOT / "dataset" / "fake",
    PROJECT_ROOT / "dataset" / "metadata",
]

missing_dirs = [str(d.relative_to(PROJECT_ROOT)) for d in required_dirs if not d.is_dir()]

if missing_dirs:
    report("File Structure", False, f"Missing: {', '.join(missing_dirs)}")
else:
    report("File Structure", True)


# ---------------------------------------------------------------------------
# 2. Dependencies
# ---------------------------------------------------------------------------
print("\n── Check 2: Dependencies ────────────────────────────────")

REQUIRED_LIBS = {
    "fastapi": "fastapi",
    "pinecone": "pinecone",
    "torch": "torch",
    "transformers": "transformers",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "ultralytics": "ultralytics",
    "sentence_transformers": "sentence-transformers",
    "streamlit": "streamlit",
    "plotly": "plotly",
    "dotenv": "python-dotenv",
    "requests": "requests",
}

# Some packages expose a different import name than their pip name.
# Try alternate import names before marking as missing.
ALTERNATE_IMPORTS = {
    "cv2": ["cv2"],
    "ultralytics": ["ultralytics"],
    "sentence_transformers": ["sentence_transformers"],
    "streamlit": ["streamlit"],
    "plotly": ["plotly"],
}

missing_libs = []
for import_name, pkg_name in REQUIRED_LIBS.items():
    try:
        __import__(import_name)
    except ImportError:
        missing_libs.append(pkg_name)

if missing_libs:
    report("Dependencies", False, f"Missing packages: {', '.join(missing_libs)}")
else:
    report("Dependencies", True)


# ---------------------------------------------------------------------------
# 3. .env Keys
# ---------------------------------------------------------------------------
print("\n── Check 3: Environment Variables (.env) ────────────────")

REQUIRED_KEYS = ["UNSPLASH_ACCESS_KEY", "HF_TOKEN", "PINECONE_API_KEY"]

env_path = BACKEND_DIR / ".env"
if not env_path.exists():
    report(".env File", False, "backend/.env not found")
else:
    missing_keys = [k for k in REQUIRED_KEYS if not ENV.get(k)]
    if missing_keys:
        report(".env Keys", False, f"Empty or missing: {', '.join(missing_keys)}")
    else:
        # Confirm non-empty without printing values
        key_status = ", ".join(f"{k}=<set>" for k in REQUIRED_KEYS)
        report(".env Keys", True, key_status)


# ---------------------------------------------------------------------------
# 4. Pinecone Connection
# ---------------------------------------------------------------------------
print("\n── Check 4: Pinecone Connection ─────────────────────────")

TARGET_INDEX = "property-ai"
EXPECTED_DIMENSION = 512
EXPECTED_METRIC = "cosine"

pinecone_api_key = ENV.get("PINECONE_API_KEY", "")
pinecone_env = ENV.get("PINECONE_ENVIRONMENT", "")

if not pinecone_api_key:
    report("Pinecone Connection", False, "PINECONE_API_KEY not set in .env")
else:
    try:
        from pinecone import Pinecone, ServerlessSpec  # pinecone-client >= 3.x

        pc = Pinecone(api_key=pinecone_api_key)

        # List indexes
        try:
            indexes = pc.list_indexes()
            index_names = [idx.name for idx in indexes]
            print(f"  Available indexes: {index_names or '(none)'}")
        except Exception as e:
            report("Pinecone Connection", False, f"Could not list indexes: {e}")
            index_names = None

        if index_names is not None:
            if TARGET_INDEX not in index_names:
                report(
                    "Pinecone Connection",
                    False,
                    f"Index '{TARGET_INDEX}' not found. Available: {index_names or 'none'}",
                )
            else:
                # Describe the index and validate spec
                desc = pc.describe_index(TARGET_INDEX)
                dim = desc.dimension
                metric = desc.metric

                issues = []
                if dim != EXPECTED_DIMENSION:
                    issues.append(f"dimension={dim} (expected {EXPECTED_DIMENSION})")
                if metric != EXPECTED_METRIC:
                    issues.append(f"metric={metric} (expected {EXPECTED_METRIC})")

                if issues:
                    report("Pinecone Connection", False, f"Index spec mismatch: {'; '.join(issues)}")
                else:
                    report(
                        "Pinecone Connection",
                        True,
                        f"Index '{TARGET_INDEX}' found, dim={dim}, metric={metric}",
                    )

    except ImportError:
        report("Pinecone Connection", False, "pinecone package not installed")
    except Exception as e:
        report("Pinecone Connection", False, str(e))


# ---------------------------------------------------------------------------
# 5. Dataset Script Syntax Check
# ---------------------------------------------------------------------------
print("\n── Check 5: Dataset Script ──────────────────────────────")

script_path = PROJECT_ROOT / "scripts" / "collect_dataset.py"

if not script_path.exists():
    report("Dataset Script", False, "scripts/collect_dataset.py not found")
else:
    try:
        source = script_path.read_text(encoding="utf-8")
        ast.parse(source)
        report("Dataset Script", True, "exists and syntax is valid")
    except SyntaxError as e:
        report("Dataset Script", False, f"Syntax error at line {e.lineno}: {e.msg}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 55)
print("SUMMARY")
print("=" * 55)
for _, msg in results:
    print(msg)

total = len(results)
passed = sum(1 for ok, _ in results if ok)
print(f"\n{passed}/{total} checks passed.")
if passed == total:
    print("🎉 All checks passed — Segment 1 is good to go!")
else:
    print("⚠️  Some checks failed. Review the output above.")
    sys.exit(1)
