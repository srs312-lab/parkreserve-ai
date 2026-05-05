from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from typing import Optional

from app.agents.reservation_agent import ReservationAgent
from app.config.settings import settings
from app.db.store import store, store_backend_name
from app.reservation_checker.campground_catalog import (
    find_campgrounds,
    lookup_campground_name,
)
from app.scheduler.jobs import (
    list_scheduler_jobs,
    pause_watch_job,
    schedule_watch_job,
    watch_check_interval_seconds,
)
from app.schemas.reservations import (
    Alert,
    AvailabilityQuery,
    AvailabilityResult,
    BatchWatchReservationResponse,
    BatchWatchReservationRequest,
    CampgroundSearchResult,
    DuplicateWatchResponse,
    IntegrationStatus,
    NextAvailabilityResult,
    ParkSearchResult,
    PauseAgentRequest,
    SettingsStatus,
    TestAlertRequest,
    TestAlertResponse,
    UserPreferences,
    Watch,
    WatchSummary,
    WatchReservationRequest,
    WatchReservationResponse,
    WatchUpdateRequest,
)

router = APIRouter()
agent = ReservationAgent()
TEST_ALERT_COOLDOWN_SECONDS = 300
last_test_alert_sent_at: Optional[datetime] = None


@router.post("/watch-reservation", response_model=WatchReservationResponse)
async def watch_reservation(
    request: WatchReservationRequest,
) -> WatchReservationResponse:
    preferences = agent.preference_agent.normalize(request)
    duplicate_watch = _find_duplicate_watch(preferences)
    if duplicate_watch is not None:
        return WatchReservationResponse(
            watch_id=duplicate_watch.watch_id,
            status=duplicate_watch.status,
            message="Duplicate watch already exists.",
        )

    watch = await agent.create_watch(request)
    schedule_watch_job(
        watch.watch_id,
        agent.check_watch,
        watch.preferences.priority,
    )
    return WatchReservationResponse(
        watch_id=watch.watch_id,
        status=watch.status,
        message="Reservation watch created.",
    )


@router.post(
    "/watch-reservations/batch",
    response_model=BatchWatchReservationResponse,
)
async def watch_reservations_batch(
    request: BatchWatchReservationRequest,
) -> BatchWatchReservationResponse:
    created: list[WatchReservationResponse] = []
    skipped_duplicates: list[DuplicateWatchResponse] = []

    for watch_request in request.watches:
        preferences = agent.preference_agent.normalize(watch_request)
        duplicate_watch = _find_duplicate_watch(preferences)
        if duplicate_watch is not None:
            skipped_duplicates.append(
                _duplicate_watch_response(duplicate_watch, preferences)
            )
            continue

        watch = await agent.create_watch(watch_request)
        schedule_watch_job(
            watch.watch_id,
            agent.check_watch,
            watch.preferences.priority,
        )
        created.append(
            WatchReservationResponse(
                watch_id=watch.watch_id,
                status=watch.status,
                message="Reservation watch created.",
            )
        )

    return BatchWatchReservationResponse(
        created=created,
        skipped_duplicates=skipped_duplicates,
    )


@router.get("/availability", response_model=list[AvailabilityResult])
async def get_availability(
    park_name: str,
    date_start: str,
    date_end: str,
    facility_id: Optional[str] = None,
    camp_type: Optional[str] = None,
    min_nights: int = 1,
) -> list[AvailabilityResult]:
    query = AvailabilityQuery(
        park_name=park_name,
        facility_id=facility_id,
        date_start=date_start,
        date_end=date_end,
        camp_type=camp_type,
        min_nights=min_nights,
    )
    return await agent.check_availability(query)


@router.get("/campgrounds/search", response_model=list[CampgroundSearchResult])
async def search_campgrounds(
    query: str,
    limit: int = 10,
) -> list[CampgroundSearchResult]:
    return await agent.search_campgrounds(query, limit=limit)


@router.get("/parks/search", response_model=list[ParkSearchResult])
async def search_parks(
    query: str,
    limit: int = 10,
) -> list[ParkSearchResult]:
    return await agent.search_parks(query, limit=limit)


@router.get("/alerts", response_model=list[Alert])
def get_alerts(watch_id: Optional[str] = None) -> list[Alert]:
    return store.list_alerts(watch_id=watch_id)


@router.post("/alerts/test", response_model=TestAlertResponse)
async def send_test_alert(request: TestAlertRequest) -> TestAlertResponse:
    global last_test_alert_sent_at

    now = datetime.now(timezone.utc)
    if last_test_alert_sent_at is not None:
        elapsed_seconds = int((now - last_test_alert_sent_at).total_seconds())
        remaining_seconds = TEST_ALERT_COOLDOWN_SECONDS - elapsed_seconds
        if remaining_seconds > 0:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Test alert cooldown is active. "
                    f"Try again in {remaining_seconds} seconds."
                ),
            )

    today = date.today()
    test_watch = Watch(
        watch_id="test-alert",
        status="active",
        preferences=UserPreferences(
            park_name="ParkReserve AI",
            date_start=today,
            date_end=today,
            camp_type="any",
            min_nights=1,
            flexibility_days=0,
            notification_type=request.notification_type,
            priority="normal",
            email_address=settings.default_alert_email,
            phone_number=settings.default_alert_phone,
        ),
    )
    test_alert = Alert(
        alert_id=str(uuid4()),
        watch_id=test_watch.watch_id,
        park_name="ParkReserve AI",
        message=(
            "Test alert: ParkReserve AI notifications are connected. "
            "No reservation was booked."
        ),
        reservation_url=settings.recreation_gov_base_url,
        created_at=now,
        campground_name="Notification Test",
        site="Test",
        available_date=today,
        available_end_date=today,
        nights=1,
        site_type="test",
    )
    deliveries = await agent.execution_agent.send_notifications(test_watch, test_alert)
    last_test_alert_sent_at = now

    return TestAlertResponse(
        message="Test alert attempted.",
        deliveries=deliveries,
        cooldown_seconds=TEST_ALERT_COOLDOWN_SECONDS,
    )


@router.post("/pause-agent")
def pause_agent(request: PauseAgentRequest) -> dict[str, str]:
    watch = store.get_watch(request.watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail="Watch not found.")

    store.pause_watch(request.watch_id)
    pause_watch_job(request.watch_id)
    return {"watch_id": request.watch_id, "status": "paused"}


@router.post("/resume-agent")
def resume_agent(request: PauseAgentRequest) -> dict[str, str]:
    watch = store.get_watch(request.watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail="Watch not found.")

    store.resume_watch(request.watch_id)
    schedule_watch_job(
        request.watch_id,
        agent.check_watch,
        watch.preferences.priority,
    )
    return {"watch_id": request.watch_id, "status": "active"}


@router.delete("/watches/{watch_id}")
def delete_watch(watch_id: str) -> dict[str, str]:
    watch = store.get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail="Watch not found.")

    pause_watch_job(watch_id)
    store.delete_watch(watch_id)
    return {"watch_id": watch_id, "status": "deleted"}


@router.patch("/watches/{watch_id}", response_model=WatchSummary)
def update_watch(watch_id: str, request: WatchUpdateRequest) -> WatchSummary:
    watch = store.get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail="Watch not found.")

    updates = request.model_dump(exclude_none=True)
    if "camp_type" in updates:
        updates["camp_type"] = updates["camp_type"].strip().lower()

    date_start = updates.get("date_start", watch.preferences.date_start)
    date_end = updates.get("date_end", watch.preferences.date_end)
    if date_start > date_end:
        raise HTTPException(
            status_code=422,
            detail="date_start must be before or equal to date_end.",
        )

    updated_preferences = watch.preferences.model_copy(update=updates)
    updated_watch = store.update_watch(watch_id, updated_preferences)

    if updated_watch.status == "active":
        schedule_watch_job(
            watch_id,
            agent.check_watch,
            updated_watch.preferences.priority,
        )

    return _watch_summary(updated_watch)


@router.get("/watches", response_model=list[WatchSummary])
def list_watches() -> list[WatchSummary]:
    return [_watch_summary(watch) for watch in store.list_watches()]


def _watch_summary(watch) -> WatchSummary:
    return WatchSummary(
        watch_id=watch.watch_id,
        status=watch.status,
        park_name=watch.preferences.park_name,
        facility_id=watch.preferences.facility_id,
        campground_name=_campground_name(
            watch.preferences.park_name,
            watch.preferences.facility_id,
            watch.preferences.campground_name,
        ),
        date_start=watch.preferences.date_start,
        date_end=watch.preferences.date_end,
        camp_type=watch.preferences.camp_type,
        min_nights=watch.preferences.min_nights,
        notification_type=watch.preferences.notification_type,
        priority=watch.preferences.priority,
        check_interval_seconds=watch_check_interval_seconds(
            watch.preferences.priority
        ),
        last_checked_at=watch.last_checked_at,
    )


def _find_duplicate_watch(preferences: UserPreferences) -> Optional[Watch]:
    target_signature = _watch_signature(preferences)
    for watch in store.list_watches():
        if _watch_signature(watch.preferences) == target_signature:
            return watch
    return None


def _watch_signature(preferences: UserPreferences) -> tuple:
    location_key = (
        "facility",
        preferences.facility_id,
    )
    if preferences.facility_id is None:
        location_key = (
            "name",
            preferences.park_name.strip().casefold(),
            (preferences.campground_name or "").strip().casefold(),
        )

    return (
        location_key,
        preferences.date_start,
        preferences.date_end,
        preferences.camp_type.strip().casefold(),
        preferences.min_nights,
        preferences.notification_type,
    )


def _duplicate_watch_response(
    watch: Watch,
    preferences: UserPreferences,
) -> DuplicateWatchResponse:
    return DuplicateWatchResponse(
        existing_watch_id=watch.watch_id,
        park_name=preferences.park_name,
        facility_id=preferences.facility_id,
        campground_name=preferences.campground_name,
        date_start=preferences.date_start,
        date_end=preferences.date_end,
        camp_type=preferences.camp_type,
        min_nights=preferences.min_nights,
        notification_type=preferences.notification_type,
        priority=preferences.priority,
        message="Duplicate watch skipped.",
    )


def _campground_name(
    park_name: str,
    facility_id: Optional[str],
    preferred_name: Optional[str] = None,
) -> Optional[str]:
    if facility_id is None:
        return preferred_name

    campgrounds = find_campgrounds(park_name, facility_id)
    if not campgrounds:
        return preferred_name or lookup_campground_name(facility_id)

    campground_name = campgrounds[0].campground_name
    if campground_name.startswith("Recreation.gov Facility"):
        return preferred_name or lookup_campground_name(facility_id)
    return campground_name


@router.post("/watches/{watch_id}/check-now", response_model=list[AvailabilityResult])
async def check_watch_now(watch_id: str) -> list[AvailabilityResult]:
    watch = store.get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail="Watch not found.")

    return await agent.check_watch(watch_id)


@router.get(
    "/watches/{watch_id}/next-available",
    response_model=list[NextAvailabilityResult],
)
async def get_next_available(
    watch_id: str,
    days: int = 90,
    limit: int = 5,
) -> list[NextAvailabilityResult]:
    watch = store.get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail="Watch not found.")

    return await agent.find_next_available(watch_id, days=days, limit=limit)


@router.get("/scheduler/jobs")
def get_scheduler_jobs() -> list[dict[str, Optional[str]]]:
    return list_scheduler_jobs()


@router.get("/db/status")
def get_db_status() -> dict[str, str]:
    return {"store": store_backend_name()}


@router.get("/settings/status", response_model=SettingsStatus)
def get_settings_status() -> SettingsStatus:
    return SettingsStatus(
        environment=settings.environment,
        store=store_backend_name(),
        poll_interval_seconds=settings.poll_interval_seconds,
        recreation_gov_base_url=settings.recreation_gov_base_url,
        ridb_api_configured=bool(settings.ridb_api_key),
        email=_email_status(),
        sms=_sms_status(),
    )


def _email_status() -> IntegrationStatus:
    provider = settings.email_provider.lower()
    if provider == "auto":
        provider = "resend" if settings.resend_api_key else "smtp"

    if provider == "smtp":
        missing = [
            name
            for name, value in [
                ("default recipient", settings.default_alert_email),
                ("SMTP host", settings.smtp_host),
                ("SMTP username", settings.smtp_username),
                ("SMTP password", settings.smtp_password),
                ("from email", settings.smtp_from_email),
            ]
            if not value
        ]

        return IntegrationStatus(
            configured=not missing,
            recipient=settings.default_alert_email,
            provider=settings.smtp_host,
            detail="configured" if not missing else f"missing {', '.join(missing)}",
        )

    missing = [
        name
        for name, value in [
            ("default recipient", settings.default_alert_email),
            ("Resend API key", settings.resend_api_key),
            ("Resend from email", settings.resend_from_email),
        ]
        if not value
    ]

    return IntegrationStatus(
        configured=not missing,
        recipient=settings.default_alert_email,
        provider="Resend HTTPS API",
        detail="configured" if not missing else f"missing {', '.join(missing)}",
    )


def _sms_status() -> IntegrationStatus:
    missing = [
        name
        for name, value in [
            ("default phone", settings.default_alert_phone),
            ("Twilio account SID", settings.twilio_account_sid),
            ("Twilio auth token", settings.twilio_auth_token),
            ("Twilio from phone", settings.twilio_from_phone),
        ]
        if not value
    ]

    return IntegrationStatus(
        configured=not missing,
        recipient=_mask_phone(settings.default_alert_phone),
        provider="Twilio" if settings.twilio_account_sid else None,
        detail="configured" if not missing else f"missing {', '.join(missing)}",
    )


def _mask_phone(phone_number: Optional[str]) -> Optional[str]:
    if not phone_number:
        return None

    digits = "".join(character for character in phone_number if character.isdigit())
    if len(digits) < 4:
        return "configured"
    return f"***-***-{digits[-4:]}"
