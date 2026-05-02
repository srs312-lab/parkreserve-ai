from datetime import datetime, timezone
from uuid import uuid4

from app.notifier.email import EmailNotifier
from app.notifier.sms import SmsNotifier
from app.schemas.reservations import (
    Alert,
    AvailabilityResult,
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
