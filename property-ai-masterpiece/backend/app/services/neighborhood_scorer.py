"""
Neighborhood Scorer — walkability, transit, amenities, safety.
Uses city profiles + property type adjustments.
In production: integrate Walk Score API, crime data APIs, Google Places.
"""
import random
from datetime import datetime
from typing import Dict, List


_CITY_PROFILES = {
    "New York":      {"walkability": 95, "transit": 95, "safety": 65, "amenities": 98},
    "San Francisco": {"walkability": 90, "transit": 85, "safety": 70, "amenities": 95},
    "Seattle":       {"walkability": 75, "transit": 65, "safety": 80, "amenities": 85},
    "Chicago":       {"walkability": 78, "transit": 72, "safety": 68, "amenities": 82},
    "Denver":        {"walkability": 60, "transit": 50, "safety": 78, "amenities": 75},
    "Austin":        {"walkability": 45, "transit": 35, "safety": 75, "amenities": 70},
    "Phoenix":       {"walkability": 42, "transit": 32, "safety": 72, "amenities": 68},
    "Miami":         {"walkability": 65, "transit": 55, "safety": 70, "amenities": 80},
}
_DEFAULT_PROFILE = {"walkability": 55, "transit": 45, "safety": 72, "amenities": 65}

_AMENITY_WEIGHTS = {
    "grocery": 0.15, "restaurant": 0.12, "cafe": 0.08,
    "park": 0.15, "school": 0.15, "transit": 0.15,
    "hospital": 0.10, "gym": 0.05, "shopping": 0.05,
}


class NeighborhoodScorer:

    def score_neighborhood(self, listing_data: Dict) -> Dict:
        city     = listing_data.get("city", "")
        state    = listing_data.get("state", "")
        zip_code = listing_data.get("zip_code", "")
        profile  = _CITY_PROFILES.get(city, _DEFAULT_PROFILE)

        # Scores with small random jitter (simulates per-address variation)
        rng = random.Random(hash(f"{city}{zip_code}"))  # deterministic per location

        walkability   = min(100, max(0, profile["walkability"]   + rng.uniform(-5, 5)))
        transit       = min(100, max(0, profile["transit"]       + rng.uniform(-8, 8)))
        safety        = min(100, max(0, profile["safety"]        + rng.uniform(-10, 10)))
        amenities     = min(100, max(0, profile["amenities"]     + rng.uniform(-5, 5)))

        # Apartment bonus for walkability
        if listing_data.get("property_type") == "apartment":
            walkability = min(100, walkability + 8)

        overall = round(
            amenities   * 0.30 +
            walkability * 0.25 +
            transit     * 0.20 +
            safety      * 0.25,
            1
        )

        return {
            "listing_id":   listing_data.get("id"),
            "location":     f"{city}, {state} {zip_code}".strip(),
            "overall_score": overall,
            "overall_grade": _grade(overall),
            "breakdown": {
                "walkability": {
                    "score":       round(walkability, 1),
                    "grade":       _grade(walkability),
                    "description": _walk_desc(walkability),
                },
                "transit": {
                    "score":       round(transit, 1),
                    "grade":       _grade(transit),
                    "description": _transit_desc(transit),
                },
                "amenities": {
                    "score":       round(amenities, 1),
                    "grade":       _grade(amenities),
                    "nearby_count": _nearby_counts(rng),
                },
                "safety": {
                    "score":       round(safety, 1),
                    "grade":       _grade(safety),
                    "description": _safety_desc(safety),
                },
            },
            "noise_level":          _noise(listing_data, rng),
            "nearby_amenities":     _sample_amenities(rng),
            "commute_estimates":    _commutes(rng),
            "neighborhood_highlights": _highlights(overall, walkability, amenities, rng),
            "data_sources": ["City profile estimates", "Would integrate Walk Score, Google Places, crime APIs"],
            "calculated_at": datetime.utcnow().isoformat(),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _grade(score: float) -> str:
    if score >= 90: return "A+"
    if score >= 85: return "A"
    if score >= 80: return "A-"
    if score >= 75: return "B+"
    if score >= 70: return "B"
    if score >= 65: return "B-"
    if score >= 60: return "C+"
    if score >= 50: return "C"
    return "D"


def _walk_desc(s: float) -> str:
    if s >= 90: return "Walker's Paradise — daily errands don't require a car"
    if s >= 70: return "Very Walkable — most errands on foot"
    if s >= 50: return "Somewhat Walkable — some errands on foot"
    if s >= 25: return "Car-Dependent — most errands require a car"
    return "Car-Dependent — almost all errands require a car"


def _transit_desc(s: float) -> str:
    if s >= 90: return "Excellent Transit — world-class public transportation"
    if s >= 70: return "Excellent Transit — many nearby options"
    if s >= 50: return "Good Transit — a few public transportation options"
    if s >= 25: return "Some Transit — minimal public transportation"
    return "Minimal Transit — car required for most trips"


def _safety_desc(s: float) -> str:
    if s >= 85: return "Very Safe — crime well below national average"
    if s >= 70: return "Safe — crime below national average"
    if s >= 55: return "Average — crime near national average"
    if s >= 40: return "Caution — crime above national average"
    return "High Risk — significantly elevated crime rates"


def _noise(listing_data: Dict, rng: random.Random) -> str:
    if listing_data.get("property_type") == "apartment":
        return rng.choice(["moderate", "elevated"])
    if (listing_data.get("square_feet") or 0) > 2000:
        return "quiet"
    return rng.choice(["quiet", "moderate"])


def _nearby_counts(rng: random.Random) -> Dict:
    return {
        "grocery_stores":  rng.randint(2, 15),
        "restaurants":     rng.randint(10, 50),
        "cafes":           rng.randint(5, 30),
        "parks":           rng.randint(1, 8),
        "schools":         rng.randint(3, 12),
        "transit_stops":   rng.randint(2, 20),
    }


def _sample_amenities(rng: random.Random) -> List[Dict]:
    pool = [
        {"name": "Whole Foods Market",  "type": "grocery",  "distance_miles": 0.4},
        {"name": "Trader Joe's",        "type": "grocery",  "distance_miles": 0.7},
        {"name": "Starbucks",           "type": "cafe",     "distance_miles": 0.2},
        {"name": "City Park",           "type": "park",     "distance_miles": 0.6},
        {"name": "Metro Station",       "type": "transit",  "distance_miles": 0.3},
        {"name": "Lincoln Elementary",  "type": "school",   "distance_miles": 0.8},
        {"name": "24 Hour Fitness",     "type": "gym",      "distance_miles": 0.5},
        {"name": "CVS Pharmacy",        "type": "shopping", "distance_miles": 0.3},
    ]
    return rng.sample(pool, k=rng.randint(4, 6))


def _commutes(rng: random.Random) -> Dict:
    return {
        "Downtown":         {"drive_min": rng.randint(10, 35), "transit_min": rng.randint(15, 50)},
        "Airport":          {"drive_min": rng.randint(20, 45), "transit_min": rng.randint(30, 70)},
        "Business District":{"drive_min": rng.randint(15, 40), "transit_min": rng.randint(20, 55)},
    }


def _highlights(overall: float, walk: float, amenities: float,
                rng: random.Random) -> List[str]:
    h = []
    if overall >= 80:  h.append("🏆 Highly desirable neighborhood")
    if walk >= 75:     h.append("🚶 Excellent walkability — daily errands on foot")
    if amenities >= 80:h.append("🛒 Abundant dining and shopping options nearby")
    extras = [
        "🌳 Close to parks and green spaces",
        "🚌 Strong public transit connections",
        "🎓 Top-rated schools in area",
        "🔒 Low crime neighborhood",
    ]
    h.append(rng.choice(extras))
    return h[:3]


_scorer = None


def get_neighborhood_scorer() -> NeighborhoodScorer:
    global _scorer
    if _scorer is None:
        _scorer = NeighborhoodScorer()
    return _scorer
