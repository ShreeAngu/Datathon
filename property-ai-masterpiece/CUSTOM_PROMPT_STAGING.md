# Custom Prompt Virtual Staging

## Overview
Users can now provide their own staging descriptions instead of selecting predefined styles.

## Features

### Two Modes Available

1. **Predefined Styles** (Quick & Easy)
   - Modern, Scandinavian, Industrial, Rustic, Luxury
   - One-click selection
   - Consistent results

2. **Custom Prompt** (Creative & Flexible)
   - Write your own staging description
   - Unlimited style possibilities
   - Personalized results

## How to Use

### Seller Dashboard
1. Go to Seller Dashboard → 🎨 Virtual Staging
2. Select a listing and image
3. Choose mode: "Predefined Styles" or "Custom Prompt"
4. If Custom Prompt:
   - Enter your staging vision (min 10 characters)
   - Be specific about furniture, colors, decor
5. Click "Generate Staged Version"

### Buyer Dashboard
1. Go to Buyer Dashboard → 🎨 Virtual Staging
2. Select a property and image
3. Choose mode: "Predefined Styles" or "Custom Prompt"
4. If Custom Prompt:
   - Describe how you'd like to see the space
5. Click "Generate Staged Version"

## Example Custom Prompts

**Good Examples:**
- "bohemian style with lots of plants, colorful textiles, and natural wood furniture"
- "Japanese zen minimalist with tatami mats, low furniture, and bamboo accents"
- "coastal beach house with light blues, whites, and natural rattan furniture"
- "art deco with geometric patterns, velvet furniture, and gold accents"
- "farmhouse chic with shiplap walls, vintage furniture, and mason jar decor"

**Tips for Best Results:**
- Be specific about style, colors, and materials
- Mention furniture types (sofa, chairs, tables)
- Include decor elements (plants, artwork, textiles)
- Keep it under 200 characters for best performance

## API Usage

```python
# Predefined style
result = api.stage_image(image_id, style="modern")

# Custom prompt
result = api.stage_image(
    image_id, 
    custom_prompt="bohemian style with plants and colorful textiles"
)
```

## Testing

```bash
cd property-ai-masterpiece
python scripts/test_custom_prompt_staging.py
```
