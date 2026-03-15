# Virtual Staging Feature Guide

## Overview
Virtual staging allows both sellers and buyers to visualize properties with AI-powered interior design transformations.

## Features

### For Sellers (Seller Dashboard → 🎨 Virtual Staging)
- Stage your own listing images before publishing
- Choose from 5 professional styles
- View before/after comparisons
- See detailed change descriptions
- ~30 seconds processing time per image

### For Buyers (Buyer Dashboard → 🎨 Virtual Staging)
- Stage any published property image
- Visualize how a property could look with different styles
- Compare multiple staging styles
- Make informed purchase decisions
- Same AI quality as seller staging

## Available Styles

1. **Modern** - Clean lines, minimalist, neutral tones
2. **Scandinavian** - Light wood, cozy textiles, white walls
3. **Industrial** - Exposed brick, metal fixtures, dark wood
4. **Rustic** - Farmhouse warmth, vintage furniture
5. **Luxury** - High-end finishes, marble, gold accents

## Technical Details

### AI Model
- **Engine**: Stable Diffusion 1.5 (img2img)
- **Hardware**: NVIDIA RTX 3050 6GB
- **Precision**: FP16 for memory efficiency
- **Processing Time**: 25-30 seconds per image
- **Resolution**: 512x512 optimized

### What's Preserved
- Wall positions and structure
- Window locations and frames
- Door frames and openings
- Ceiling height and features
- Room dimensions and layout

### What's Changed
- Furniture style and placement
- Flooring materials and colors
- Wall colors and textures
- Lighting and ambiance
- Decor and accessories

## API Endpoints

### Stage Image
```
POST /api/v1/stage?image_id={id}&style={style}
Authorization: Bearer {token}
```

**Parameters:**
- `image_id` (required): Image UUID from database
- `style` (required): modern | scandinavian | industrial | rustic | luxury

**Response:**
```json
{
  "success": true,
  "style": "modern",
  "tier": "Local SD 1.5 (AI Generated)",
  "processing_time": 27.5,
  "staged_image_url": "/images/staged/...",
  "original_image_url": "/images/uploads/...",
  "changes_made": ["Added modern sofa...", "..."],
  "preserved_elements": ["Wall positions...", "..."],
  "structure_preserved": true
}
```

### Get Listing Images (Buyer)
```
GET /api/v1/buyer/listings/{listing_id}
Authorization: Bearer {token}
```

Returns full listing details including all images for published listings.

## Usage Examples

### Seller Workflow
1. Login as seller
2. Go to Seller Dashboard → 🎨 Virtual Staging
3. Select a listing with images
4. Choose an image to stage
5. Pick a style (e.g., "modern")
6. Click "Generate Staged Version"
7. Wait ~30 seconds
8. View before/after comparison

### Buyer Workflow
1. Login as buyer
2. Go to Buyer Dashboard → 🎨 Virtual Staging
3. Browse published properties
4. Select a property with images
5. Choose an image to stage
6. Pick a style to visualize
7. Click "Generate Staged Version"
8. Compare different styles

## Testing

### Test Seller Staging
```bash
cd property-ai-masterpiece
python scripts/test_staging.py
```

### Test Buyer Staging
```bash
cd property-ai-masterpiece
python scripts/test_buyer_staging.py
```

## Performance Notes

- First staging request may take longer (~35s) due to model loading
- Subsequent requests are faster (~25-30s)
- GPU memory is automatically cleared after each request
- Fallback to PIL enhancement if GPU unavailable

## Future Enhancements

- [ ] Batch staging (multiple images at once)
- [ ] Custom style prompts
- [ ] Higher resolution output (1024x1024)
- [ ] Furniture removal mode
- [ ] Room type detection and style suggestions
- [ ] Save staged images to listing
- [ ] Compare multiple styles side-by-side
- [ ] Mobile-optimized staging
