# Analyze Section Features ✅

## Summary

Added a comprehensive image analysis section to the Seller Dashboard with AI detection review, accept/reject functionality, quality metrics, and keyword generation.

## New Features

### 1. 🔍 Analyze Images Tab

A dedicated tab in the Seller Dashboard that displays all uploaded images with their AI analysis results.

**Features:**
- Visual display of each image with analysis data
- AI detection results with confidence scores
- Quality metrics (Overall, Lighting, Clutter, Room Type)
- Recommendations for improvement
- Accept/Reject buttons for each image

**Confidence Threshold:**
- Only shows confidence scores if >= 70%
- Hides low-confidence predictions to avoid confusion

### 2. ✅ Accept & Reject Images

**Accept (Keep in Listing):**
- Confirms the image is acceptable
- Image remains in the listing
- Contributes to overall quality score

**Reject (Remove from Listing):**
- Deletes the image from the listing
- Removes image file from storage
- Recalculates listing quality score
- Updates authenticity verification status

**Auto-recalculation:**
- Quality score updates automatically after deletion
- Authenticity flag updates if all AI images removed

### 3. 📊 Quality Score Display

Each image shows:
- **Overall Quality**: 0-100 composite score
- **Lighting Score**: 0-100 brightness/contrast quality
- **Clutter Score**: 0-100 (100 = no clutter)
- **Room Type**: Detected room category

Listing quality score is the average of all image quality scores.

### 4. 🔑 Keyword Generation

Automatically extracts keywords from listing descriptions using NLP.

**Algorithm:**
1. Tokenizes description text
2. Filters out stop words (a, the, is, etc.)
3. Prioritizes property-specific keywords (modern, luxury, spacious, etc.)
4. Includes frequent words (appearing 2+ times)
5. Returns top 30 keywords

**Property Keywords Prioritized:**
- Style: modern, luxury, spacious, updated, renovated, elegant, contemporary
- Features: kitchen, bedroom, bathroom, pool, deck, patio, balcony, fireplace
- Materials: hardwood, granite, marble, stainless
- Location: downtown, waterfront, view, neighborhood, walkable
- Amenities: parking, storage, laundry, utilities, pet-friendly

**Example:**
```
Description: "Beautiful modern condo with stunning views. Features include 
hardwood floors, granite countertops, stainless steel appliances..."

Keywords: granite, shopping, laundry, parking, balcony, stainless, 
appliances, beautiful, spacious, transit, location, stunning, prime, 
hardwood, dining, downtown, modern, condo, views, features, floors, 
countertops, steel, facilities, friendly, building
```

## API Endpoints

### GET /seller/listings/{lid}/analysis
Returns AI analysis data for all images in a listing.

**Response:**
```json
{
  "listing_id": "abc123",
  "image_count": 2,
  "analyses": [
    {
      "image": {
        "id": "img123",
        "original_filename": "bedroom.jpg",
        "image_url": "/images/uploads/img123_bedroom.jpg"
      },
      "analysis": {
        "room_type": "bedroom",
        "overall_quality_score": 81.8,
        "lighting_quality_score": 90.0,
        "clutter_score": 100.0,
        "trust_score": 100.0,
        "is_ai_generated": 0,
        "ai_probability": 0.0,
        "recommendations": "[...]"
      }
    }
  ]
}
```

### DELETE /seller/listings/{lid}/images/{image_id}
Deletes an image and recalculates listing quality.

**Response:**
```json
{
  "status": "deleted",
  "image_id": "img123"
}
```

### POST /seller/listings
Creates a listing and returns generated keywords.

**Response:**
```json
{
  "status": "created",
  "listing_id": "abc123",
  "keywords": ["modern", "luxury", "spacious", ...]
}
```

## UI Flow

1. **Upload Images** → Upload & Validate tab
2. **Review Analysis** → Analyze Images tab
   - View each image with AI detection results
   - See quality scores and recommendations
   - Check confidence levels (only shown if >= 70%)
3. **Accept or Reject**
   - ✅ Accept: Keep image in listing
   - ❌ Reject: Remove from listing
4. **Auto-update** → Quality score recalculates automatically

## Confidence Score Logic

```python
# Only show confidence if >= 70%
confidence_threshold = 70
ai_prob = analysis.get("ai_probability", 0)
real_prob = 100 - ai_prob

show_confidence = max(ai_prob, real_prob) >= confidence_threshold

if show_confidence:
    # Display the confidence metric
    if is_ai:
        st.metric("AI Probability", f"{ai_prob:.1f}%")
    else:
        st.metric("Trust Score", f"{trust_score:.1f}/100")
```

## Testing

Run the test script:
```bash
python scripts/test_analyze_section.py
```

This tests:
1. Getting analysis data for a listing
2. Deleting an image and verifying quality score update
3. Keyword generation from description

## Benefits

1. **Transparency**: Sellers see exactly what AI detected
2. **Control**: Sellers can override AI decisions
3. **Quality**: Automatic quality scoring helps improve listings
4. **SEO**: Keywords improve searchability
5. **Trust**: Confidence threshold prevents showing uncertain predictions

## Future Enhancements

- Bulk accept/reject all images
- Edit keywords manually
- Export analysis report as PDF
- Compare before/after quality scores
- Suggest optimal image order based on quality
