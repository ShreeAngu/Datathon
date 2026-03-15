"""
AI-Generated Image Detection using Hugging Face Organika/sdxl-detector model.
This model is specifically trained to detect SDXL-generated images.
"""

import numpy as np
from PIL import Image
from pathlib import Path

_model = None
_processor = None


def _load_model():
    """Load the Hugging Face SDXL detector model."""
    global _model, _processor
    if _model is not None:
        return _model, _processor
    
    try:
        from transformers import AutoImageProcessor, AutoModelForImageClassification
        import torch
        
        print("[Authenticity HF] Loading Organika/sdxl-detector model...")
        _processor = AutoImageProcessor.from_pretrained("Organika/sdxl-detector")
        _model = AutoModelForImageClassification.from_pretrained("Organika/sdxl-detector")
        
        # Move to GPU if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = _model.to(device)
        _model.eval()
        
        print(f"[Authenticity HF] Model loaded on {device}")
        return _model, _processor
    except Exception as e:
        print(f"[Authenticity HF] Failed to load model: {e}")
        return None, None


def detect_ai_generated(image_path: str) -> dict:
    """
    Detect if an image is AI-generated using Organika/sdxl-detector.
    
    Returns:
        is_ai_generated: bool - True if AI-generated
        trust_score: float (0-100) - 100 = definitely real, 0 = definitely AI
        confidence: float (0-1) - How confident the model is
        real_probability: float (0-1) - Probability of being real
        ai_probability: float (0-1) - Probability of being AI-generated
    """
    model, processor = _load_model()
    
    if model is None or processor is None:
        # Fallback to simple heuristic if model fails to load
        return {
            "is_ai_generated": False,
            "trust_score": 50.0,
            "confidence": 0.0,
            "real_probability": 0.5,
            "ai_probability": 0.5,
            "model_available": False,
            "error": "Model not available"
        }
    
    try:
        import torch
        
        # Load and preprocess image
        img = Image.open(image_path).convert("RGB")
        
        # Process image
        inputs = processor(images=img, return_tensors="pt")
        
        # Move to same device as model
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get predictions
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probabilities = torch.nn.functional.softmax(logits, dim=-1)
        
        # Get probabilities for each class
        probs = probabilities[0].cpu().numpy()
        
        # Check model config to determine class order
        if len(probs) == 2:
            # Check if model has id2label mapping
            if hasattr(model.config, 'id2label'):
                labels = model.config.id2label
                # Find which index corresponds to which class
                if 'artificial' in labels.get(0, '').lower() or 'fake' in labels.get(0, '').lower() or 'synthetic' in labels.get(0, '').lower():
                    # Class 0 is AI-generated, Class 1 is real
                    ai_prob = float(probs[0])
                    real_prob = float(probs[1])
                else:
                    # Class 0 is real, Class 1 is AI-generated
                    real_prob = float(probs[0])
                    ai_prob = float(probs[1])
            else:
                # Default assumption: [real, fake]
                real_prob = float(probs[0])
                ai_prob = float(probs[1])
        else:
            # Fallback if unexpected number of classes
            real_prob = 0.5
            ai_prob = 0.5
        
        # Determine if AI-generated (threshold at 0.5)
        is_ai_generated = ai_prob > real_prob
        
        # Trust score: 0-100 scale (100 = definitely real)
        trust_score = round(real_prob * 100, 1)
        
        # Confidence: how far from 0.5 (uncertain)
        confidence = round(abs(max(real_prob, ai_prob) - 0.5) * 2, 3)
        
        return {
            "is_ai_generated": bool(is_ai_generated),
            "trust_score": trust_score,
            "confidence": confidence,
            "real_probability": round(real_prob, 4),
            "ai_probability": round(ai_prob, 4),
            "model_available": True,
            "model_name": "Organika/sdxl-detector"
        }
        
    except Exception as e:
        print(f"[Authenticity HF] Detection error: {e}")
        return {
            "is_ai_generated": False,
            "trust_score": 50.0,
            "confidence": 0.0,
            "real_probability": 0.5,
            "ai_probability": 0.5,
            "model_available": False,
            "error": str(e)
        }


def detect_authenticity(image_path: str) -> dict:
    """
    Main authenticity detection function (compatible with existing code).
    Uses Hugging Face SDXL detector for AI detection.
    
    Returns dict with keys:
        - trust_score: 0-100 (100 = definitely real)
        - is_fake: bool
        - detection_confidence: 0-1
        - is_ai_generated: bool (alias for is_fake)
    """
    result = detect_ai_generated(image_path)
    
    # Convert to format expected by existing code
    return {
        "trust_score": result["trust_score"],
        "is_fake": result["is_ai_generated"],
        "is_ai_generated": result["is_ai_generated"],
        "detection_confidence": result["confidence"],
        "real_probability": result.get("real_probability", 0.5),
        "ai_probability": result.get("ai_probability", 0.5),
        "model_available": result.get("model_available", False),
        "model_name": result.get("model_name", "Organika/sdxl-detector"),
        "artifacts_detected": ["ai_generated"] if result["is_ai_generated"] else [],
    }
