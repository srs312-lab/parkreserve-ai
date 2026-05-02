from datetime import date, datetime, timedelta
from urllib.parse import quote

import httpx

from app.config.settings import settings
from app.reservation_checker.campground_catalog import Campground, find_campgrounds
from app.schemas.reservations import (
    AvailabilityQuery,
    AvailabilityResult,
    CampgroundSearchResult,
    ParkSearchResult,
)


class RecreationGovClient:
    def __init__(self) -> None:
        self.base_url = settings.recreation_gov_base_url.rstrip("/")

    async def check_availability(
        self,
        query: AvailabilityQuery,
    ) -> list[AvailabilityResult]:
        if query.facility_id and query.campground_name:
            campgrounds = [
                Campground(
                    facility_id=query.facility_id,
                    park_name=query.park_name,
                    campground_name=query.campground_name,
                )
            ]
        else:
            campgrounds = find_campgrounds(query.park_name, query.facility_id)
        if not campgrounds and not query.facility_id:
            search_results = await self.search_campgrounds(query.park_name, limit=3)
            campgrounds = [
                Campground(
                    facility_id=result.facility_id,
                    park_name=query.park_name,
                    campground_name=result.name,
                )
                for result in search_results
            ]

        results: list[AvailabilityResult] = []

        async with httpx.AsyncClient(timeout=20) as client:
            for campground in campgrounds:
                for month_start in _month_starts(query.date_start, query.date_end):
                    payload = await self._fetch_month(client, campground, month_start)
                    results.extend(
                        self._parse_month(payload, campground, query),
                    )

        return sorted(
            results,
            key=lambda result: (
                result.available_date,
                result.campground_name,
                result.site,
            ),
        )

    async def search_campgrounds(
        self,
        query: str,
        limit: int = 10,
    ) -> list[CampgroundSearchResult]:
        search_text = query
        if "campground" not in query.lower():
            search_text = f"{query} campground"

        params = {
            "query": search_text,
            "entity_type": "campground",
            "size": limit,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/api/search", params=params)
            response.raise_for_status()
            payload = response.json()

        campgrounds: list[CampgroundSearchResult] = []
        for item in payload.get("results", []):
            facility_id = str(item.get("entity_id", ""))
            if not facility_id:
                continue
            if not item.get("campsites_count"):
                continue

            address = _first_address(item)
            campgrounds.append(
                CampgroundSearchResult(
                    facility_id=facility_id,
                    name=item.get("name", f"Facility {facility_id}"),
                    park_name=query,
                    city=item.get("city") or address.get("city"),
                    state_code=address.get("state_code"),
                    reservation_url=f"{self.base_url}/camping/campgrounds/{facility_id}",
                )
            )

        return campgrounds

    async def search_parks(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ParkSearchResult]:
        params = {
            "query": query,
            "entity_type": "recarea",
            "size": limit * 2,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/api/search", params=params)
            response.raise_for_status()
            payload = response.json()

        parks: list[ParkSearchResult] = []
        seen_names: set[str] = set()
        for item in payload.get("results", []):
            if item.get("entity_type") != "recarea":
                continue

            name = item.get("name", "").strip()
            recarea_id = str(item.get("entity_id", ""))
            if not name or not recarea_id or name.lower() in seen_names:
                continue

            seen_names.add(name.lower())
            parks.append(
                ParkSearchResult(
                    recarea_id=recarea_id,
                    name=name,
                    state_code=item.get("state_code"),
                    campgrounds_count=_int_value(item.get("campgrounds_count")),
                )
            )

            if len(parks) >= limit:
                break

        return parks

    async def _fetch_month(
        self,
        client: httpx.AsyncClient,
        campground: Campground,
        month_start: date,
    ) -> dict:
        start_date = quote(f"{month_start.isoformat()}T00:00:00.000Z")
        url = (
            f"{self.base_url}/api/camps/availability/campground/"
            f"{campground.facility_id}/month?start_date={start_date}"
        )
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

    def _parse_month(
        self,
        payload: dict,
        campground: Campground,
        query: AvailabilityQuery,
    ) -> list[AvailabilityResult]:
        results: list[AvailabilityResult] = []

        for campsite in payload.get("campsites", {}).values():
            site_type = campsite.get("campsite_type", "unknown")

            if query.camp_type and not _camp_type_matches(query.camp_type, site_type):
                continue

            available_dates: list[date] = []
            for raw_date, status in campsite.get("availabilities", {}).items():
                available_date = datetime.fromisoformat(
                    raw_date.replace("Z", "+00:00"),
                ).date()

                if not query.date_start <= available_date <= query.date_end:
                    continue

                if status != "Available":
                    continue

                available_dates.append(available_date)

            for available_date, available_end_date, nights in _available_stays(
                available_dates,
                query.min_nights,
            ):
                results.append(
                    AvailabilityResult(
                        park_name=campground.park_name,
                        campground_name=campground.campground_name,
                        facility_id=campground.facility_id,
                        campsite_id=str(campsite.get("campsite_id", "")),
                        site=str(campsite.get("site", "")),
                        status="Available",
                        available=True,
                        available_date=available_date,
                        available_end_date=available_end_date,
                        nights=nights,
                        site_type=site_type,
                        price=None,
                        is_weekend=available_date.weekday() >= 5,
                        source="recreation.gov",
                        reservation_url=(
                            f"{self.base_url}/camping/campgrounds/"
                            f"{campground.facility_id}"
                        ),
                    )
                )

        return results


def _month_starts(date_start: date, date_end: date) -> list[date]:
    current = date_start.replace(day=1)
    final = date_end.replace(day=1)
    months: list[date] = []

    while current <= final:
        months.append(current)
        next_month = current.replace(day=28) + timedelta(days=4)
        current = next_month.replace(day=1)

    return months


def _camp_type_matches(requested: str, site_type: str) -> bool:
    requested = requested.strip().lower()
    site_type = site_type.strip().lower()

    if requested in {"any", "all"}:
        return True

    if requested == "tent":
        return "tent" in site_type or "standard" in site_type

    return requested in site_type


def _available_stays(
    available_dates: list[date],
    min_nights: int,
) -> list[tuple[date, date, int]]:
    dates = sorted(set(available_dates))
    if not dates:
        return []

    stays: list[tuple[date, date, int]] = []
    run_start = dates[0]
    previous = dates[0]

    for current in dates[1:]:
        if current == previous + timedelta(days=1):
            previous = current
            continue

        _add_stay(stays, run_start, previous, min_nights)
        run_start = current
        previous = current

    _add_stay(stays, run_start, previous, min_nights)
    return stays


def _add_stay(
    stays: list[tuple[date, date, int]],
    run_start: date,
    run_end: date,
    min_nights: int,
) -> None:
    nights = (run_end - run_start).days + 1
    if nights < min_nights:
        return
    stays.append((run_start, run_end, nights))


def _first_address(item: dict) -> dict:
    addresses = item.get("addresses") or []
    if not addresses:
        return {}
    return addresses[0]


def _int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
