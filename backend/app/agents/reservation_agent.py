from datetime import date, datetime, timedelta, timezone
from typing import Optional

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

        results = await self.search_agent.search(watch.preferences.to_availability_query())
        ranked_results = self.decision_agent.rank(results, watch.preferences)

        new_results = [
            result
            for result in ranked_results
            if not store.has_alerted(watch.watch_id, result)
        ]

        if new_results:
            alert = self.execution_agent.create_alert(watch, new_results[0])
            deliveries = await self.execution_agent.send_notifications(watch, alert)
            alert = alert.model_copy(update={"deliveries": deliveries})
            store.add_alert(alert)

        for result in ranked_results:
            store.mark_alerted(watch.watch_id, result)

        store.mark_watch_checked(watch.watch_id, datetime.now(timezone.utc))
        return ranked_results

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
