"""Authenticity verification — Hugging Face SDXL detector + forensic fallback."""

from pathlib import Path


def verify_authenticity(image_path: str, dataset_label: str = None) -> dict:
    """
    Primary: Hugging Face Organika/sdxl-detector model.
    Fallback: forensic heuristics if model fails to load.
    """
    # --- Try Hugging Face SDXL detector ---
    hf_result    = None
    hf_available = False
    try:
        from app.models.authenticity_hf_model import detect_ai_generated
        hf_result    = detect_ai_generated(image_path)
        hf_available = hf_result.get("model_available", False)
    except Exception as e:
        print(f"⚠️  HF detector error: {e}")

    # --- Forensic analysis (always run for EXIF / lighting data) ---
    try:
        from app.models.authenticity_forensic import analyze_forensics
        forensic = analyze_forensics(image_path)
    except Exception:
        forensic = {"trust_score": 50, "exif_valid": False,
                    "lighting_consistent": True, "noise_variance": 50,
                    "artifacts_detected": []}

    if hf_available and hf_result:
        # Blend HF model (75%) with forensic analysis (25%)
        trust_score = round(hf_result["trust_score"] * 0.75
                            + forensic.get("trust_score", 50) * 0.25, 1)
        is_ai       = hf_result["is_ai_generated"]
        confidence  = hf_result["confidence"]
        ai_prob     = round(hf_result["ai_probability"] * 100, 1)
        real_prob   = round(hf_result["real_probability"] * 100, 1)
        method      = f"Hugging Face ({hf_result.get('model_name', 'SDXL Detector')})"
    else:
        # Fallback to forensic only
        trust_score = forensic.get("trust_score", 50)
        is_ai       = trust_score < 50
        confidence  = round(abs(trust_score - 50) / 50, 3)
        ai_prob     = round(100 - trust_score, 1)
        real_prob   = round(trust_score, 1)
        method      = "Forensic Heuristics (HF model unavailable)"

    conf_level = ("HIGH"   if max(ai_prob, real_prob) > 80 else
                  "MEDIUM" if max(ai_prob, real_prob) > 60 else "LOW")

    return {
        "trust_score":          trust_score,
        "is_ai_generated":      is_ai,
        "detection_confidence": confidence,
        "ai_probability":       ai_prob,
        "real_probability":     real_prob,
        "exif_valid":           forensic.get("exif_valid", False),
        "lighting_consistent":  forensic.get("lighting_consistent", True),
        "noise_variance":       forensic.get("noise_variance", 0),
        "artifacts_detected":   forensic.get("artifacts_detected", []),
        "detection_method":     method,
        "confidence_level":     conf_level,
        "forensic_score":       forensic.get("trust_score", 50),
        "ground_truth_label":   dataset_label,
        "model_available":      hf_available,
    }
