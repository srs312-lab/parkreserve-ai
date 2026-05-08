from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import uuid4

from app.config.settings import settings
from app.notifier.email import EmailNotifier
from app.notifier.sms import SmsNotifier
from app.schemas.reservations import (
    Alert,
    AvailabilityResult,
    BookingIntent,
    NotificationDelivery,
    Watch,
)


class ExecutionAgent:
    def __init__(self) -> None:
        self.email_notifier = EmailNotifier()
        self.sms_notifier = SmsNotifier()

    def create_alert(self, watch: Watch, result: AvailabilityResult) -> Alert:
        return Alert(
            alert_id=str(uuid4()),
            watch_id=watch.watch_id,
            park_name=result.park_name,
            message=(
                f"Found {result.site_type} site {result.site} at "
                f"{result.campground_name} for {result.nights} night"
                f"{'' if result.nights == 1 else 's'} from "
                f"{result.available_date} to {result.available_end_date}."
            ),
            reservation_url=result.reservation_url,
            created_at=datetime.now(timezone.utc),
            campground_name=result.campground_name,
            facility_id=result.facility_id,
            campsite_id=result.campsite_id,
            site=result.site,
            available_date=result.available_date,
            available_end_date=result.available_end_date,
            nights=result.nights,
            site_type=result.site_type,
        )

    def create_booking_intent(self, alert: Alert) -> BookingIntent:
        created_at = datetime.now(timezone.utc)
        return BookingIntent(
            booking_intent_id=str(uuid4()),
            alert_id=alert.alert_id,
            watch_id=alert.watch_id,
            status="created",
            handoff_url=_booking_handoff_url(alert),
            created_at=created_at,
            updated_at=created_at,
            park_name=alert.park_name,
            campground_name=alert.campground_name,
            facility_id=alert.facility_id,
            campsite_id=alert.campsite_id,
            site=alert.site,
            available_date=alert.available_date,
            available_end_date=alert.available_end_date,
            nights=alert.nights,
            site_type=alert.site_type,
            note=(
                "Book Assist opens Recreation.gov with the matching campground "
                "and dates. The user must verify availability, rules, price, "
                "and complete checkout manually."
            ),
        )

    async def send_notifications(self, watch: Watch, alert: Alert) -> list[NotificationDelivery]:
        notification_type = watch.preferences.notification_type
        deliveries: list[NotificationDelivery] = []

        if notification_type in {"email", "both"}:
            status, detail = await self.email_notifier.send(
                alert,
                watch.preferences.email_address,
            )
            deliveries.append(
                NotificationDelivery(channel="email", status=status, detail=detail)
            )

        if notification_type in {"sms", "both"}:
            status, detail = await self.sms_notifier.send(
                alert,
                watch.preferences.phone_number,
            )
            deliveries.append(
                NotificationDelivery(channel="sms", status=status, detail=detail)
            )

        return deliveries

    async def retry_notifications(
        self,
        watch: Watch,
        alert: Alert,
        channels: set[str],
    ) -> list[NotificationDelivery]:
        deliveries: list[NotificationDelivery] = []

        if "email" in channels:
            status, detail = await self.email_notifier.send(
                alert,
                watch.preferences.email_address,
            )
            deliveries.append(
                NotificationDelivery(channel="email", status=status, detail=detail)
            )

        if "sms" in channels:
            status, detail = await self.sms_notifier.send(
                alert,
                watch.preferences.phone_number,
            )
            deliveries.append(
                NotificationDelivery(channel="sms", status=status, detail=detail)
            )

        return deliveries


def _booking_handoff_url(alert: Alert) -> str:
    base_url = settings.recreation_gov_base_url.rstrip("/")
    if not alert.facility_id:
        return alert.reservation_url or base_url

    params: dict[str, str] = {}
    if alert.available_date:
        params["checkin"] = alert.available_date.isoformat()
    if alert.available_end_date:
        checkout_date = alert.available_end_date + timedelta(days=1)
        params["checkout"] = checkout_date.isoformat()
    if alert.campsite_id:
        params["campsite_id"] = alert.campsite_id

    query_string = f"?{urlencode(params)}" if params else ""
    return f"{base_url}/camping/campgrounds/{alert.facility_id}{query_string}"
