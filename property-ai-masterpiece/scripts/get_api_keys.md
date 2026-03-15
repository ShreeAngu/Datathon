# Free API Keys for Dataset Collection

## Already configured in backend/.env
- ✅ `UNSPLASH_ACCESS_KEY` — set
- ✅ `HF_TOKEN` — set (used for HuggingFace fake datasets)

## Optional: Pexels (300 more real images)
1. Go to https://www.pexels.com/api/
2. Sign up for free account
3. Get API key from dashboard
4. Add to `backend/.env`: `PEXELS_API_KEY=your_key`

## Optional: Pixabay (300 more real images)
1. Go to https://pixabay.com/api/docs/
2. Sign up for free account
3. Get API key
4. Add to `backend/.env`: `PIXABAY_API_KEY=your_key`

## HuggingFace Datasets Used (no extra setup needed)
- `dima806/real_vs_fake_images_detection` — 400 fake images
- `Hemg/fake-and-real-images` — 300 fake images
- `competitions/aiornot` — 200 fake images

## Execution Order
```bash
# From property-ai-masterpiece/ directory:

# 1. Collect real images via Unsplash (~30 mins)
python scripts/collect_real_images.py

# 2. Collect fake images via HuggingFace (~40 mins, needs internet)
python scripts/collect_fake_images.py

# 3. Validate dataset
python scripts/validate_dataset.py

# 4. Retrain with EfficientNet-B0 (~30 mins on RTX 3050)
python scripts/retrain_fake_detector.py

# 5. Test accuracy
python scripts/test_authenticity.py
```
