# Hybrid Search System

## Overview
Advanced 3-tier search combining SQL filters, keyword matching, and AI semantic ranking.

## Search Tiers

### Tier 1: SQL Filters (Fast)
Traditional database filtering:
- Location (city, state)
- Price range
- Bedrooms/bathrooms
- Property type
- Square footage
- Quality score
- Authenticity verification

### Tier 2: Keyword Matching (Medium)
Text search in listing fields:
- Title
- Description
- Uses SQL LIKE for pattern matching
- Case-insensitive

### Tier 3: Semantic Ranking (Smart)
AI-powered relevance scoring:
- Uses CLIP embeddings
- Understands context and meaning
- Ranks by semantic similarity
- Optional (toggle on/off)

## How It Works

### Without Semantic Ranking
1. Apply SQL filters
2. Search keywords in title/description
3. Return results ordered by publish date

### With Semantic Ranking
1. Apply SQL filters
2. Search keywords in title/description
3. Generate CLIP embedding for query
4. Generate CLIP embedding for each listing
5. Calculate cosine similarity
6. Rank by relevance score

## Usage Examples

### Keyword Search Only
```
Query: "smart home"
Results: Listings with "smart home" in title/description
```

### Keyword + Semantic Ranking
```
Query: "exposed brick"
Smart Ranking: ON
Results: Listings ranked by AI relevance (60.25%, 45.12%, etc.)
```

### Hybrid Search
```
Query: "solar"
Max Price: $600K
Smart Ranking: ON
Results: Listings with "solar" under $600K, ranked by relevance
```

## UI Features

### Buyer Dashboard Sidebar

**🔤 Keyword Search**
- Text input for search queries
- Examples: "modern kitchen", "waterfront", "cozy"

**🧠 Smart Ranking**
- Checkbox to enable AI ranking
- Slower but more intelligent results
- Shows relevance scores (e.g., 🎯 60.25%)

**📍 Location Filters**
- City and state search

**💰 Price & Size Filters**
- Price range slider
- Property type dropdown
- Min bedrooms/bathrooms

**✨ Quality Filters**
- Min quality score
- Verified authentic only

## API Endpoint

```
GET /api/v1/buyer/search/advanced
```

### Parameters
- `query` (string): Keyword search text
- `semantic_rank` (bool): Enable AI ranking
- `city` (string): Filter by city
- `state` (string): Filter by state
- `min_price` (float): Minimum price
- `max_price` (float): Maximum price
- `min_beds` (int): Minimum bedrooms
- `property_type` (string): house, apartment, condo, etc.
- `min_quality` (float): Minimum quality score (0-100)
- `verified_only` (bool): Only verified listings
- `page` (int): Page number
- `per_page` (int): Results per page (max 100)

### Response
```json
{
  "total": 5,
  "page": 1,
  "per_page": 20,
  "pages": 1,
  "semantic_ranking_enabled": true,
  "listings": [
    {
      "id": "...",
      "title": "Industrial Loft Apartment",
      "semantic_score": 0.6025,
      "price": 290000,
      ...
    }
  ]
}
```

## Performance

| Search Type | Speed | Accuracy |
|-------------|-------|----------|
| SQL Filters Only | ~50ms | Exact |
| + Keyword Match | ~100ms | Good |
| + Semantic Rank | ~2-5s | Excellent |

## Testing

```bash
cd property-ai-masterpiece
python scripts/test_hybrid_search_real.py
```

## Example Queries

**Good Keyword Queries:**
- "smart home"
- "exposed brick"
- "updated kitchen"
- "solar panels"
- "waterfront"

**Good Semantic Queries:**
- "rustic farmhouse style"
- "modern minimalist design"
- "family-friendly neighborhood"
- "luxury finishes"
