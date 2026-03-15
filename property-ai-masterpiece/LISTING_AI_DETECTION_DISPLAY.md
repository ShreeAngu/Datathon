# AI Detection Display in Listings ✅

## Summary

Added real-time AI detection status display for all images directly in the "My Listings" section of the Seller Dashboard.

## Feature

### Display Format

Each listing now shows all images with their AI detection status:

```
📸 Images:
✅ bedroom_photo.jpg - Real (100%)
🤖 kitchen_render.jpg - AI Generated (98%)
✅ bathroom.jpg - Real (95%)
❓ living_room.jpg - Uncertain
```

### Status Icons

- **✅ Real** - Image detected as authentic photograph
- **🤖 AI Generated** - Image detected as AI-generated
- **❓ Uncertain** - Confidence below 70% threshold

### Confidence Display

**Shows confidence percentage when >= 70%:**
- Real images: Shows real probability (e.g., "Real (95%)")
- AI images: Shows AI probability (e.g., "AI Generated (98%)")

**Hides confidence when < 70%:**
- Shows "Uncertain" instead of confusing low-confidence scores
- Prevents misleading information

## Implementation

### Code Logic

```python
# Get analysis data for listing
analysis_data = api.get_listing_analysis(listing_id)

for item in analysis_data["analyses"]:
    analysis = item.get("analysis", {})
    is_ai = analysis.get("is_ai_generated") == 1
    ai_prob = analysis.get("ai_probability", 0)
    
    # Only show confidence if >= 70%
    show_confidence = max(ai_prob, 100 - ai_prob) >= 70
    
    if is_ai:
        if show_confidence:
            display = f"🤖 {filename} - AI Generated ({ai_prob:.0f}%)"
        else:
            display = f"❓ {filename} - Uncertain"
    else:
        if show_confidence:
            display = f"✅ {filename} - Real ({100-ai_prob:.0f}%)"
        else:
            display = f"❓ {filename} - Uncertain"
```

## UI Location

**Seller Dashboard → My Listings Tab**

Each listing expander shows:
1. Location and property details
2. Primary image thumbnail
3. **📸 Images section** (NEW)
   - Lists all images with AI detection status
   - Shows confidence percentage if >= 70%
4. Quality score metrics
5. Publish/Delete buttons
6. Edit form

## Example Display

```
🟢 Modern 3BR Downtown Condo — $450,000 [published]
├─ 📍 Seattle, WA
├─ Type: condo  Beds: 3  Baths: 2  Sqft: 1200
├─ [Primary photo thumbnail]
├─ 📸 Images:
│  ├─ ✅ living_room.jpg - Real (100%)
│  ├─ ✅ kitchen.jpg - Real (98%)
│  ├─ 🤖 bedroom_staged.jpg - AI Generated (99%)
│  └─ ✅ bathroom.jpg - Real (95%)
├─ Quality: 85/100
└─ [Publish] [Delete]
```

## Benefits

1. **Immediate Visibility**: Sellers see AI detection status without navigating to Analyze tab
2. **Quick Review**: Can quickly scan all listings for AI-generated images
3. **Confidence Transparency**: Shows how certain the AI is about each detection
4. **Uncertainty Handling**: Clearly marks low-confidence predictions as "Uncertain"
5. **Action Prompt**: Sellers can immediately go to Analyze tab to accept/reject flagged images

## User Flow

1. **Upload images** → Images analyzed automatically
2. **View My Listings** → See AI detection status for each image
3. **Identify issues** → Spot AI-generated or uncertain images
4. **Take action** → Go to Analyze tab to accept/reject
5. **Verify** → Return to My Listings to confirm changes

## Confidence Threshold Logic

**Why 70%?**
- Below 70%: Model is uncertain, showing percentage could mislead
- At 70%+: Model is confident enough to show specific probability
- Prevents false confidence in borderline cases

**Examples:**
- 100% AI → Show "AI Generated (100%)"
- 95% Real → Show "Real (95%)"
- 75% AI → Show "AI Generated (75%)"
- 65% Real → Show "Uncertain" (below threshold)
- 55% AI → Show "Uncertain" (below threshold)

## Testing

The feature automatically loads when viewing listings. To test:

1. Upload images with AI detection
2. Go to "My Listings" tab
3. Expand any listing
4. See "📸 Images:" section with detection status

## Future Enhancements

- Color-coded badges (green for real, red for AI)
- Click image name to jump to Analyze tab
- Bulk actions from listing view
- Filter listings by AI detection status
- Export detection report
