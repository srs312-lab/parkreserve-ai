from app.reservation_checker.recreation_gov import RecreationGovClient
from app.schemas.reservations import (
    AvailabilityQuery,
    AvailabilityResult,
    CampgroundSearchResult,
    ParkSearchResult,
)


class SearchAgent:
    def __init__(self) -> None:
        self.recreation_gov = RecreationGovClient()

    async def search(self, query: AvailabilityQuery) -> list[AvailabilityResult]:
        return await self.recreation_gov.check_availability(query)

    async def search_campgrounds(
        self,
        query: str,
        limit: int = 10,
    ) -> list[CampgroundSearchResult]:
        return await self.recreation_gov.search_campgrounds(query, limit=limit)

    async def search_parks(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ParkSearchResult]:
        return await self.recreation_gov.search_parks(query, limit=limit)
