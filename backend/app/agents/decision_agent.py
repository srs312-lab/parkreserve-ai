from app.ranking_engine.scorer import score_result
from app.schemas.reservations import AvailabilityResult, UserPreferences


class DecisionAgent:
    def rank(
        self,
        results: list[AvailabilityResult],
        preferences: UserPreferences,
    ) -> list[AvailabilityResult]:
        ranked = sorted(
            results,
            key=lambda result: score_result(result, preferences),
            reverse=True,
        )
        return ranked
