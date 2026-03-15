"""
Investment Analyzer — estimates ROI, rental yield, and market position
based on listing data and comparable properties.
"""
from app.database.connection import fetchall, fetchone


def analyze_investment(listing_id: str = None, price: float = None,
                       square_feet: int = None, bedrooms: int = None,
                       city: str = None, state: str = None,
                       quality_score: float = None) -> dict:
    """
    Returns investment metrics for a property.
    Can work from a listing_id or raw parameters.
    """
    # Load from DB if listing_id provided
    if listing_id:
        row = fetchone("SELECT * FROM listings WHERE id=?", (listing_id,))
        if row:
            price         = price         or row.get("price", 0)
            square_feet   = square_feet   or row.get("square_feet")
            bedrooms      = bedrooms      or row.get("bedrooms")
            city          = city          or row.get("city")
            state         = state         or row.get("state")
            quality_score = quality_score or row.get("overall_quality_score")

    price = price or 0

    # Comparable listings in same city/state
    comps = []
    if city or state:
        filters = []
        params  = []
        if city:
            filters.append("city=?")
            params.append(city)
        if state:
            filters.append("state=?")
            params.append(state)
        params.append(listing_id or "")
        where = " AND ".join(filters) + " AND id!=? AND price>0 AND status='published'"
        comps = fetchall(f"SELECT price, square_feet, bedrooms FROM listings WHERE {where}",
                         tuple(params))

    # Price per sqft
    ppsf = None
    if square_feet and square_feet > 0 and price > 0:
        ppsf = round(price / square_feet, 2)

    # Market average ppsf from comps
    market_ppsf = None
    comp_prices = [c["price"] for c in comps if c.get("price")]
    if comps:
        valid = [c["price"] / c["square_feet"]
                 for c in comps if c.get("square_feet") and c.get("price")]
        if valid:
            market_ppsf = round(sum(valid) / len(valid), 2)

    # Estimated monthly rent (1% rule approximation)
    est_monthly_rent = round(price * 0.008, 0)  # 0.8% of price
    if bedrooms:
        est_monthly_rent += bedrooms * 150  # bedroom premium

    # Gross rental yield
    gross_yield = round((est_monthly_rent * 12 / price * 100), 2) if price > 0 else 0

    # Net yield estimate (subtract ~35% for expenses)
    net_yield = round(gross_yield * 0.65, 2)

    # Cap rate estimate
    noi = est_monthly_rent * 12 * 0.65
    cap_rate = round(noi / price * 100, 2) if price > 0 else 0

    # Market position
    position = "market_rate"
    if market_ppsf and ppsf:
        diff_pct = (ppsf - market_ppsf) / market_ppsf * 100
        if diff_pct < -10:
            position = "below_market"
        elif diff_pct > 10:
            position = "above_market"

    # Quality premium
    quality_premium = 0.0
    if quality_score:
        quality_premium = round((quality_score - 70) / 100 * 0.10, 3)

    # Investment score (0-100)
    inv_score = 50
    inv_score += min(20, gross_yield * 3)
    if position == "below_market":
        inv_score += 15
    elif position == "above_market":
        inv_score -= 10
    if quality_score:
        inv_score += (quality_score - 50) * 0.2
    inv_score = round(min(100, max(0, inv_score)), 1)

    return {
        "listing_id":           listing_id,
        "purchase_price":       price,
        "price_per_sqft":       ppsf,
        "market_avg_ppsf":      market_ppsf,
        "market_position":      position,
        "estimated_monthly_rent": round(est_monthly_rent, 0),
        "gross_rental_yield":   gross_yield,
        "net_rental_yield":     net_yield,
        "cap_rate":             cap_rate,
        "quality_premium":      quality_premium,
        "investment_score":     inv_score,
        "comparable_count":     len(comps),
        "recommendation":       _investment_recommendation(inv_score, position, gross_yield),
    }


def _investment_recommendation(score: float, position: str, yield_: float) -> str:
    if score >= 75:
        return "Strong buy — excellent investment fundamentals"
    if score >= 60:
        return "Good investment — solid rental yield potential"
    if score >= 45:
        if position == "below_market":
            return "Potential value play — priced below market"
        return "Average investment — consider negotiating price"
    return "Caution — limited investment upside at current price"
