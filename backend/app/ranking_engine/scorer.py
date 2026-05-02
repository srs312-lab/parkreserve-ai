from app.schemas.reservations import AvailabilityResult, UserPreferences


def score_result(result: AvailabilityResult, preferences: UserPreferences) -> int:
    score = 0

    if result.available:
        score += 100

    if preferences.camp_type in result.site_type.lower():
        score += 25

    if preferences.max_price is not None and result.price is not None:
        if result.price <= preferences.max_price:
            score += 15
        else:
            score -= 20

    if preferences.weekend_preferred and result.is_weekend:
        score += 10

    score += min(result.nights, 7) * 3

    return score
