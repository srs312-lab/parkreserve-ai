from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from app.agents.decision_agent import DecisionAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.preference_agent import PreferenceAgent
from app.agents.search_agent import SearchAgent
from app.db.store import store
from app.schemas.reservations import (
    AvailabilityQuery,
    AvailabilityResult,
    CampgroundSearchResult,
    NextAvailabilityResult,
    ParkSearchResult,
    ReservationCheckLog,
    StrategyRecommendation,
    Watch,
    WatchReservationRequest,
)


class ReservationAgent:
    def __init__(self) -> None:
        self.preference_agent = PreferenceAgent()
        self.search_agent = SearchAgent()
        self.decision_agent = DecisionAgent()
        self.execution_agent = ExecutionAgent()

    async def create_watch(self, request: WatchReservationRequest) -> Watch:
        preferences = self.preference_agent.normalize(request)
        watch = store.create_watch(preferences)
        await self.check_watch(watch.watch_id)
        return store.get_watch(watch.watch_id) or watch

    async def check_watch(self, watch_id: str) -> list[AvailabilityResult]:
        watch = store.get_watch(watch_id)
        if watch is None or watch.status != "active":
            return []

        checked_at = datetime.now(timezone.utc)
        try:
            results = await self.search_agent.search(
                watch.preferences.to_availability_query()
            )
            ranked_results = self.decision_agent.rank(results, watch.preferences)

            new_results = [
                result
                for result in ranked_results
                if not store.has_alerted(watch.watch_id, result)
            ]

            alert_created = False
            if new_results:
                alert = self.execution_agent.create_alert(watch, new_results[0])
                deliveries = await self.execution_agent.send_notifications(watch, alert)
                alert = alert.model_copy(update={"deliveries": deliveries})
                store.add_alert(alert)
                alert_created = True

            for result in ranked_results:
                store.mark_alerted(watch.watch_id, result)

            store.add_check_log(
                ReservationCheckLog(
                    log_id=str(uuid4()),
                    watch_id=watch.watch_id,
                    checked_at=checked_at,
                    status="success",
                    result_count=len(ranked_results),
                    alert_created=alert_created,
                    top_match_summary=(
                        _top_match_summary(ranked_results[0])
                        if ranked_results
                        else "No matching availability found."
                    ),
                )
            )
            store.mark_watch_checked(watch.watch_id, checked_at)
            return ranked_results
        except Exception as error:
            store.add_check_log(
                ReservationCheckLog(
                    log_id=str(uuid4()),
                    watch_id=watch.watch_id,
                    checked_at=checked_at,
                    status="failed",
                    error_message=str(error),
                )
            )
            store.mark_watch_checked(watch.watch_id, checked_at)
            raise

    async def check_availability(
        self,
        query: AvailabilityQuery,
    ) -> list[AvailabilityResult]:
        return await self.search_agent.search(query)

    async def search_campgrounds(
        self,
        query: str,
        limit: int = 10,
    ) -> list[CampgroundSearchResult]:
        return await self.search_agent.search_campgrounds(query, limit=limit)

    async def search_parks(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ParkSearchResult]:
        return await self.search_agent.search_parks(query, limit=limit)

    async def find_next_available(
        self,
        watch_id: str,
        days: int = 90,
        limit: int = 5,
        from_date: Optional[date] = None,
    ) -> list[NextAvailabilityResult]:
        watch = store.get_watch(watch_id)
        if watch is None:
            return []

        search_start = from_date or date.today()
        search_end = search_start + timedelta(days=days)
        query = AvailabilityQuery(
            park_name=watch.preferences.park_name,
            facility_id=watch.preferences.facility_id,
            date_start=search_start,
            date_end=search_end,
            camp_type=watch.preferences.camp_type,
            min_nights=watch.preferences.min_nights,
        )
        results = await self.search_agent.search(query)
        grouped = _group_next_availability(results)
        return grouped[:limit]

    async def recommend_watch_strategy(
        self,
        watch_id: str,
        days: int = 90,
        limit: int = 6,
    ) -> list[StrategyRecommendation]:
        watch = store.get_watch(watch_id)
        if watch is None:
            return []

        recommendations: list[StrategyRecommendation] = []
        seen_keys: set[tuple[str, date, date, int]] = set()

        exact_results = await self.search_agent.search(
            watch.preferences.to_availability_query()
        )
        exact_openings = _group_next_availability(
            self.decision_agent.rank(exact_results, watch.preferences)
        )
        recommendations.extend(
            _strategy_recommendations(
                watch_id,
                exact_openings,
                "exact_match",
                "Matches the selected watch window and filters.",
                100,
                seen_keys,
                limit - len(recommendations),
            )
        )

        if len(recommendations) < limit:
            same_park_results: list[AvailabilityResult] = []
            campgrounds = await self.search_agent.search_campgrounds(
                watch.preferences.park_name,
                limit=8,
            )
            for campground in campgrounds:
                if campground.facility_id == watch.preferences.facility_id:
                    continue
                try:
                    same_park_results.extend(
                        await self.search_agent.search(
                            watch.preferences.to_availability_query().model_copy(
                                update={
                                    "facility_id": campground.facility_id,
                                    "campground_name": campground.name,
                                }
                            )
                        )
                    )
                except Exception:
                    continue

            same_park_openings = _group_next_availability(
                self.decision_agent.rank(same_park_results, watch.preferences)
            )
            recommendations.extend(
                _strategy_recommendations(
                    watch_id,
                    same_park_openings,
                    "same_park",
                    "Same-park campground alternative inside the selected window.",
                    75,
                    seen_keys,
                    limit - len(recommendations),
                )
            )

        if len(recommendations) < limit:
            search_start = date.today()
            search_end = search_start + timedelta(days=days)
            flexible_results = await self.search_agent.search(
                watch.preferences.to_availability_query().model_copy(
                    update={
                        "date_start": search_start,
                        "date_end": search_end,
                    }
                )
            )
            flexible_openings = [
                opening
                for opening in _group_next_availability(
                    self.decision_agent.rank(flexible_results, watch.preferences)
                )
                if (
                    opening.available_date < watch.preferences.date_start
                    or opening.available_date > watch.preferences.date_end
                )
            ]
            recommendations.extend(
                _strategy_recommendations(
                    watch_id,
                    flexible_openings,
                    "flexible_date",
                    f"Same campground outside the selected window within {days} days.",
                    55,
                    seen_keys,
                    limit - len(recommendations),
                )
            )

        return sorted(
            recommendations,
            key=lambda recommendation: (
                -recommendation.score,
                recommendation.available_date,
                recommendation.campground_name,
            ),
        )[:limit]


def _group_next_availability(
    results: list[AvailabilityResult],
) -> list[NextAvailabilityResult]:
    grouped: dict[tuple[str, str, date, date, int], dict] = {}

    for result in results:
        key = (
            result.facility_id,
            result.campground_name,
            result.available_date,
            result.available_end_date,
            result.nights,
        )
        if key not in grouped:
            grouped[key] = {
                "park_name": result.park_name,
                "campground_name": result.campground_name,
                "facility_id": result.facility_id,
                "available_date": result.available_date,
                "available_end_date": result.available_end_date,
                "nights": result.nights,
                "site_ids": set(),
                "site_types": set(),
                "reservation_url": result.reservation_url,
            }

        grouped[key]["site_ids"].add(result.campsite_id)
        grouped[key]["site_types"].add(result.site_type)

    openings = [
        NextAvailabilityResult(
            park_name=value["park_name"],
            campground_name=value["campground_name"],
            facility_id=value["facility_id"],
            available_date=value["available_date"],
            available_end_date=value["available_end_date"],
            nights=value["nights"],
            site_count=len(value["site_ids"]),
            site_types=sorted(value["site_types"]),
            reservation_url=value["reservation_url"],
        )
        for value in grouped.values()
    ]
    return sorted(
        openings,
        key=lambda opening: (
            opening.available_date,
            -opening.nights,
            opening.campground_name,
        ),
    )


def _strategy_recommendations(
    watch_id: str,
    openings: list[NextAvailabilityResult],
    match_type: str,
    reason: str,
    base_score: int,
    seen_keys: set[tuple[str, date, date, int]],
    limit: int,
) -> list[StrategyRecommendation]:
    recommendations: list[StrategyRecommendation] = []
    for opening in openings:
        key = (
            opening.facility_id,
            opening.available_date,
            opening.available_end_date,
            opening.nights,
        )
        if key in seen_keys:
            continue

        seen_keys.add(key)
        recommendations.append(
            StrategyRecommendation(
                recommendation_id=":".join(
                    [
                        match_type,
                        opening.facility_id,
                        opening.available_date.isoformat(),
                        str(opening.nights),
                    ]
                ),
                watch_id=watch_id,
                match_type=match_type,
                park_name=opening.park_name,
                campground_name=opening.campground_name,
                facility_id=opening.facility_id,
                available_date=opening.available_date,
                available_end_date=opening.available_end_date,
                nights=opening.nights,
                site_count=opening.site_count,
                site_types=opening.site_types,
                reason=reason,
                score=base_score + min(opening.site_count, 10) + opening.nights,
                reservation_url=opening.reservation_url,
            )
        )
        if len(recommendations) >= limit:
            break

    return recommendations


def _top_match_summary(result: AvailabilityResult) -> str:
    return (
        f"{result.campground_name} site {result.site} for {result.nights} "
        f"night{'' if result.nights == 1 else 's'} from "
        f"{result.available_date} to {result.available_end_date}."
    )
