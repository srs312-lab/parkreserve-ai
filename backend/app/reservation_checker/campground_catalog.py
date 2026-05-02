from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass(frozen=True)
class Campground:
    facility_id: str
    park_name: str
    campground_name: str


CAMPGROUNDS: dict[str, list[Campground]] = {
    "yosemite national park": [
        Campground(
            facility_id="232449",
            park_name="Yosemite National Park",
            campground_name="North Pines Campground",
        ),
        Campground(
            facility_id="232447",
            park_name="Yosemite National Park",
            campground_name="Upper Pines Campground",
        ),
        Campground(
            facility_id="232450",
            park_name="Yosemite National Park",
            campground_name="Lower Pines Campground",
        ),
        Campground(
            facility_id="10083845",
            park_name="Yosemite National Park",
            campground_name="Tamarack Flat Campground",
        ),
        Campground(
            facility_id="232452",
            park_name="Yosemite National Park",
            campground_name="Crane Flat Campground",
        ),
    ],
    "joshua tree national park": [
        Campground(
            facility_id="232470",
            park_name="Joshua Tree National Park",
            campground_name="Sheep Pass Group",
        ),
        Campground(
            facility_id="232473",
            park_name="Joshua Tree National Park",
            campground_name="Black Rock Campground",
        ),
        Campground(
            facility_id="232471",
            park_name="Joshua Tree National Park",
            campground_name="Cottonwood Group",
        ),
    ],
}


def find_campgrounds(park_name: str, facility_id: Optional[str] = None) -> list[Campground]:
    normalized_park = park_name.strip().lower()

    if facility_id:
        for campgrounds in CAMPGROUNDS.values():
            for campground in campgrounds:
                if campground.facility_id == facility_id:
                    return [campground]

        return [
            Campground(
                facility_id=facility_id,
                park_name=park_name,
                campground_name=f"Recreation.gov Facility {facility_id}",
            )
        ]

    return CAMPGROUNDS.get(normalized_park, [])


def lookup_campground_name(facility_id: str) -> Optional[str]:
    try:
        response = httpx.get(
            f"https://www.recreation.gov/api/camps/campgrounds/{facility_id}",
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        return None

    campground = response.json().get("campground", {})
    name = campground.get("facility_name")
    if not name:
        return None

    return _title_case_campground(name)


def _title_case_campground(name: str) -> str:
    words = []
    for word in name.split():
        if len(word) <= 3 and word.isupper():
            words.append(word)
        else:
            words.append(word.capitalize())
    return " ".join(words)
