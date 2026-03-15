"""
Forensic authenticity detector — upgraded multi-signal approach.
Combines: DCT frequency analysis, noise residuals, colour statistics,
EXIF validation, and EfficientNet-B0 deep features for robust detection.
"""

import numpy as np
from PIL import Image, ExifTags
from pathlib import Path

# ---------------------------------------------------------------------------
# Signal 1: Noise residual analysis (SRM-inspired)
# ---------------------------------------------------------------------------

def _noise_residual_features(arr: np.ndarray) -> dict:
    """Extract noise residual via multiple high-pass filters."""
    from scipy.ndimage import convolve
    gray = arr.mean(axis=2).astype(np.float32)

    # 3 different high-pass kernels
    k1 = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=np.float32)
    k2 = np.array([[-1, 2, -1]], dtype=np.float32)
    k3 = np.array([[-1], [2], [-1]], dtype=np.float32)

    r1 = convolve(gray, k1)
    r2 = convolve(gray, k2)
    r3 = convolve(gray, k3)

    return {
        "var_lap":  float(np.var(r1)),
        "var_h":    float(np.var(r2)),
        "var_v":    float(np.var(r3)),
        "kurtosis": float(_kurtosis(r1.flatten())),
    }


def _kurtosis(x: np.ndarray) -> float:
    mu = x.mean()
    sigma = x.std() + 1e-9
    return float(np.mean(((x - mu) / sigma) ** 4))


# ---------------------------------------------------------------------------
# Signal 2: DCT frequency domain analysis
# ---------------------------------------------------------------------------

def _dct_features(arr: np.ndarray) -> dict:
    """
    AI images have characteristic frequency signatures.
    Real photos have more high-frequency energy from sensor noise.
    """
    from scipy.fft import dct
    gray = arr.mean(axis=2).astype(np.float32)

    # Sample 8x8 blocks and compute DCT energy distribution
    h, w = gray.shape
    block_size = 8
    high_freq_ratios = []
    block_variances = []

    for r in range(0, h - block_size, block_size * 2):
        for c in range(0, w - block_size, block_size * 2):
            block = gray[r:r+block_size, c:c+block_size]
            d = dct(dct(block.T, norm='ortho').T, norm='ortho')
            total_energy = np.sum(d**2) + 1e-9
            # High frequency = bottom-right quadrant
            high_energy = np.sum(d[4:, 4:]**2)
            high_freq_ratios.append(high_energy / total_energy)
            block_variances.append(float(np.var(block)))

    # Block boundary discontinuities
    boundary_diffs = []
    for r in range(8, h, 8):
        boundary_diffs.append(float(np.abs(gray[r-1, :w] - gray[r, :w]).mean()))
    for c in range(8, w, 8):
        boundary_diffs.append(float(np.abs(gray[:h, c-1] - gray[:h, c]).mean()))

    return {
        "high_freq_ratio":   float(np.mean(high_freq_ratios)) if high_freq_ratios else 0.0,
        "high_freq_std":     float(np.std(high_freq_ratios)) if high_freq_ratios else 0.0,
        "block_var_mean":    float(np.mean(block_variances)) if block_variances else 0.0,
        "boundary_diff":     float(np.mean(boundary_diffs)) if boundary_diffs else 0.0,
    }


# ---------------------------------------------------------------------------
# Signal 3: Colour & texture statistics
# ---------------------------------------------------------------------------

def _colour_features(arr: np.ndarray) -> dict:
    """Statistical features from colour channels."""
    features = {}
    for i, ch in enumerate(['r', 'g', 'b']):
        channel = arr[:, :, i].astype(np.float32)
        features[f'{ch}_std']      = float(channel.std())
        features[f'{ch}_kurtosis'] = float(_kurtosis(channel.flatten()))

    # Colour correlation between channels (AI images often have higher correlation)
    r, g, b = arr[:,:,0].flatten().astype(float), arr[:,:,1].flatten().astype(float), arr[:,:,2].flatten().astype(float)
    features['rg_corr'] = float(np.corrcoef(r, g)[0, 1])
    features['rb_corr'] = float(np.corrcoef(r, b)[0, 1])

    # Local Binary Pattern-like texture measure
    gray = arr.mean(axis=2).astype(np.float32)
    features['texture_entropy'] = float(_entropy(gray))

    return features


def _entropy(gray: np.ndarray) -> float:
    hist, _ = np.histogram(gray, bins=256, range=(0, 256))
    hist = hist / (hist.sum() + 1e-9)
    hist = hist[hist > 0]
    return float(-np.sum(hist * np.log2(hist)))


# ---------------------------------------------------------------------------
# Signal 4: EXIF validation
# ---------------------------------------------------------------------------

def _check_exif(image_path: str) -> tuple[bool, list[str]]:
    flags = []
    try:
        img  = Image.open(image_path)
        exif = img._getexif()
        if exif is None:
            flags.append("no_exif")
            return False, flags
        tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        if "Make" not in tags and "Model" not in tags:
            flags.append("no_camera_make_model")
        if "DateTimeOriginal" not in tags:
            flags.append("no_capture_datetime")
        has_camera = "Make" in tags or "Model" in tags
        return has_camera, flags
    except Exception:
        return False, ["exif_read_error"]


# ---------------------------------------------------------------------------
# Signal 5: Deep feature anomaly (EfficientNet-B0 via torchvision)
# ---------------------------------------------------------------------------

_deep_model = None

def _get_deep_model():
    global _deep_model
    if _deep_model is not None:
        return _deep_model
    try:
        import torch
        import torchvision.models as models
        import torchvision.transforms as T

        model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        model.eval()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)

        transform = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        _deep_model = (model, transform, device)
        return _deep_model
    except Exception as e:
        return None


def _deep_features(img: Image.Image) -> dict:
    """Extract penultimate layer features and compute anomaly score."""
    result = _get_deep_model()
    if result is None:
        return {"deep_score": 0.5, "deep_available": False}

    import torch
    model, transform, device = result

    try:
        x = transform(img).unsqueeze(0).to(device)
        with torch.no_grad():
            # Hook into avgpool output
            features = []
            def hook(m, i, o): features.append(o.squeeze().cpu().numpy())
            h = model.avgpool.register_forward_hook(hook)
            model(x)
            h.remove()

        feat = features[0]  # shape: (1280,)

        # AI-generated images tend to have lower feature variance
        # and different activation patterns in high-level features
        feat_var    = float(np.var(feat))
        feat_max    = float(feat.max())
        sparsity    = float((feat < 0.01).mean())  # fraction of near-zero activations

        # Empirically tuned: real photos have higher variance and sparsity
        deep_score = min(1.0, max(0.0,
            feat_var / 0.15 * 0.4 +
            sparsity * 0.4 +
            min(1.0, feat_max / 5.0) * 0.2
        ))
        return {"deep_score": deep_score, "deep_available": True,
                "feat_var": feat_var, "sparsity": sparsity}
    except Exception as e:
        return {"deep_score": 0.5, "deep_available": False}


# ---------------------------------------------------------------------------
# Main detector — weighted ensemble
# ---------------------------------------------------------------------------

def detect_authenticity(image_path: str) -> dict:
    """
    Returns:
        trust_score         : 0-100 (100 = definitely real camera photo)
        is_fake             : bool
        detection_confidence: 0-1
        exif_valid          : bool
        noise_variance      : float
        colour_smoothness   : float
        artifacts_detected  : list[str]
    """
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)

    # --- Gather all signals ---
    try:
        noise = _noise_residual_features(arr)
    except Exception:
        noise = {"var_lap": 50.0, "var_h": 10.0, "var_v": 10.0, "kurtosis": 3.0}

    try:
        dct = _dct_features(arr)
    except Exception:
        dct = {"high_freq_ratio": 0.1, "high_freq_std": 0.05,
               "block_var_mean": 100.0, "boundary_diff": 2.0}

    try:
        colour = _colour_features(arr)
    except Exception:
        colour = {"r_std": 50.0, "texture_entropy": 7.0, "rg_corr": 0.9}

    exif_valid, exif_flags = _check_exif(image_path)
    deep = _deep_features(img)

    artifacts = list(exif_flags)

    # --- Component scores (0-100, higher = more real) ---

    # Noise: real photos have higher Laplacian variance
    noise_score = min(100.0, noise["var_lap"] / 8.0)

    # DCT: real photos have more high-freq energy and higher boundary diffs
    dct_score = (
        min(100.0, dct["high_freq_ratio"] * 500) * 0.4 +
        min(100.0, dct["boundary_diff"] * 15)    * 0.4 +
        min(100.0, dct["high_freq_std"] * 1000)  * 0.2
    )

    # Colour: real photos have higher channel std and texture entropy
    colour_score = (
        min(100.0, colour.get("r_std", 50) / 0.8)       * 0.3 +
        min(100.0, colour.get("texture_entropy", 7) * 12) * 0.4 +
        max(0.0, 100 - colour.get("rg_corr", 0.9) * 80)  * 0.3
    )

    # EXIF
    exif_score = 75.0 if exif_valid else 30.0

    # Deep features
    deep_score = deep["deep_score"] * 100

    # --- Weighted ensemble ---
    if deep["deep_available"]:
        trust_score = (
            noise_score  * 0.20 +
            dct_score    * 0.20 +
            colour_score * 0.15 +
            exif_score   * 0.15 +
            deep_score   * 0.30
        )
    else:
        trust_score = (
            noise_score  * 0.30 +
            dct_score    * 0.30 +
            colour_score * 0.25 +
            exif_score   * 0.15
        )

    trust_score = round(min(100.0, max(0.0, trust_score)), 1)

    # Artifact flags
    if noise["var_lap"] < 30:
        artifacts.append("low_noise_variance")
    if dct["high_freq_ratio"] < 0.02:
        artifacts.append("low_dct_high_freq")
    if colour.get("rg_corr", 0) > 0.97:
        artifacts.append("high_channel_correlation")
    if deep.get("sparsity", 1.0) < 0.3:
        artifacts.append("low_feature_sparsity")

    is_fake    = trust_score < 50
    confidence = round(abs(trust_score - 50) / 50, 3)

    return {
        "trust_score":          trust_score,
        "is_fake":              is_fake,
        "detection_confidence": confidence,
        "exif_valid":           exif_valid,
        "noise_variance":       round(noise["var_lap"], 2),
        "colour_smoothness":    round(1.0 - min(1.0, colour.get("texture_entropy", 7) / 8), 4),
        "artifacts_detected":   artifacts,
        # debug signals
        "_noise_score":  round(noise_score, 1),
        "_dct_score":    round(dct_score, 1),
        "_colour_score": round(colour_score, 1),
        "_exif_score":   round(exif_score, 1),
        "_deep_score":   round(deep_score, 1),
        "_deep_avail":   deep["deep_available"],
    }
