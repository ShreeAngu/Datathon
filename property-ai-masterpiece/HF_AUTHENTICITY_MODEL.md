# Hugging Face Authenticity Detection Model

## Overview
Replaced custom-trained MobileNetV3 model with Hugging Face `Organika/sdxl-detector` for AI-generated image detection.

## Model Details

**Model:** Organika/sdxl-detector  
**Source:** Hugging Face Transformers  
**Purpose:** Detect SDXL-generated images  
**Type:** Binary classification (real/ai-generated)  
**Size:** 347MB

## Why This Change?

### Previous Approach
- Custom MobileNetV3-Small trained on 570 images
- 93.67% validation accuracy
- Required local training and model files
- Limited to specific AI generation patterns

### New Approach
- Pre-trained Hugging Face model
- Specifically designed for SDXL detection
- No local training required
- Better generalization
- Regular updates from community

## Implementation

### Model Loading
```python
from transformers import AutoImageProcessor, AutoModelForImageClassification

processor = AutoImageProcessor.from_pretrained("Organika/sdxl-detector")
model = AutoModelForImageClassification.from_pretrained("Organika/sdxl-detector")
```

### Detection Function
```python
from app.models.authenticity_hf_model import detect_ai_generated

result = detect_ai_generated("path/to/image.jpg")
# Returns:
# {
#   "is_ai_generated": False,
#   "trust_score": 100.0,
#   "confidence": 1.0,
#   "real_probability": 1.0,
#   "ai_probability": 0.0,
#   "model_available": True
# }
```

## Integration

### Authenticity Service
The service now uses:
1. **Primary:** Hugging Face SDXL detector (75% weight)
2. **Secondary:** Forensic analysis (25% weight)
3. **Fallback:** Forensic only if HF model unavailable

### Blending Strategy
```python
trust_score = hf_result["trust_score"] * 0.75 + forensic_score * 0.25
```

## Performance

| Metric | Value |
|--------|-------|
| Model Size | 347MB |
| Load Time | ~16s (first time) |
| Inference Time | ~100-200ms |
| GPU Memory | ~2GB |
| Accuracy | High (pre-trained) |

## Test Results

### Real Image
```
Is AI Generated: False
Trust Score: 100.0/100
Confidence: 100.00%
Real Probability: 100.00%
AI Probability: 0.00%
```

### AI-Generated Image
```
Is AI Generated: True
Trust Score: 0.0/100
Confidence: 100.00%
Real Probability: 0.02%
AI Probability: 99.98%
```

## Room Classification

**Important:** Room classification still uses the old detection model (YOLO + spatial analysis).

The HF model is ONLY used for:
- AI-generated detection
- Authenticity verification
- Trust score calculation

Room type detection continues to use:
- YOLO object detection
- Spatial analysis
- Custom room classification logic

## API Response

### Before (Custom Model)
```json
{
  "trust_score": 94.2,
  "is_ai_generated": false,
  "detection_method": "Local DL (val_acc=93.67%)",
  "confidence_level": "HIGH"
}
```

### After (HF Model)
```json
{
  "trust_score": 87.3,
  "is_ai_generated": false,
  "detection_method": "Hugging Face (Organika/sdxl-detector)",
  "confidence_level": "HIGH",
  "model_available": true,
  "real_probability": 100.0,
  "ai_probability": 0.0
}
```

## Advantages

### Accuracy
- ✅ Pre-trained on large dataset
- ✅ Specifically designed for SDXL detection
- ✅ Regular community updates
- ✅ Better generalization

### Maintenance
- ✅ No local training required
- ✅ No model files to manage
- ✅ Automatic updates via Hugging Face
- ✅ Community support

### Deployment
- ✅ Easy to deploy (pip install transformers)
- ✅ Works on CPU and GPU
- ✅ Cached after first download
- ✅ Standard Hugging Face interface

## Disadvantages

### Size
- ❌ 347MB model (vs 14MB custom model)
- ❌ Longer first-time load (~16s)

### Dependencies
- ❌ Requires transformers library
- ❌ Requires internet for first download

### Specificity
- ❌ Optimized for SDXL (may miss other AI generators)
- ❌ Less control over training data

## Migration Notes

### Files Kept
- `authenticity_model.py` - Forensic analysis (still used)
- `authenticity_forensic.py` - EXIF/noise analysis (still used)
- `detection_model.py` - YOLO for room detection (still used)
- `spatial_service.py` - Room classification (still used)

### Files Added
- `authenticity_hf_model.py` - New HF model wrapper

### Files Deprecated
- `fake_detector_inference.py` - Old custom model (not used)
- `fake_detector_model.py` - Old training code (not used)
- `fake_detector_final.pt` - Old model weights (not used)

## Testing

```bash
cd property-ai-masterpiece
python scripts/test_hf_authenticity.py
```

## Future Enhancements

- [ ] Support multiple AI detector models
- [ ] Ensemble of detectors for better accuracy
- [ ] Fine-tune on property-specific images
- [ ] Add detection for other AI generators (Midjourney, DALL-E)
- [ ] Model quantization for faster inference

## Configuration

### Environment Variables
```bash
# Optional: Set Hugging Face cache directory
HF_HOME=/path/to/cache

# Optional: Disable symlink warnings on Windows
HF_HUB_DISABLE_SYMLINKS_WARNING=1
```

### GPU Support
Model automatically uses GPU if available:
```python
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)
```

## Troubleshooting

### Model Download Issues
If model fails to download:
```bash
# Manual download
huggingface-cli download Organika/sdxl-detector
```

### Memory Issues
If GPU memory insufficient:
```python
# Model will fallback to CPU automatically
# Or increase GPU memory allocation
```

### Slow First Load
First load downloads 347MB model:
- Subsequent loads use cached model (~1s)
- Consider pre-downloading in deployment

---

**Version:** 2.0.0  
**Last Updated:** March 15, 2026  
**Status:** Production Ready
