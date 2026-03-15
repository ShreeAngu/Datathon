from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class Recommendation(BaseModel):
    priority: str  # high, medium, low
    action: str
    impact: str
    auto_fixable: bool = False


class ImageValidationResponse(BaseModel):
    image_id: str
    verified_room_type: str
    room_confidence: float
    matches_expected: bool
    lighting_score: float
    lighting_feedback: str
    clutter_score: float
    clutter_locations: List[str]
    clutter_heatmap_path: Optional[str]
    is_ai_generated: bool
    ai_probability: float
    is_duplicate: bool
    duplicate_listing_id: Optional[str]
    composition_score: float
    composition_issues: List[str]
    overall_quality: float
    recommendations: List[Dict[str, Any]]
    auto_enhance_available: bool


class ReverseSearchResponse(BaseModel):
    query_image_id: str
    matches: List[Dict[str, Any]]
    total_found: int
    search_time_ms: float
