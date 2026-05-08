from datetime import datetime
from uuid import uuid4
from typing import Optional

from app.schemas.reservations import (
    Alert,
    AvailabilityResult,
    BookingIntent,
    BookingIntentStatus,
    NotificationDelivery,
    ReservationCheckLog,
    UserPreferences,
    Watch,
)


class MemoryStore:
    def __init__(self) -> None:
        self.watches: dict[str, Watch] = {}
        self.alerts: list[Alert] = []
        self.alert_keys: set[str] = set()
        self.check_logs: list[ReservationCheckLog] = []
        self.booking_intents: list[BookingIntent] = []

    def create_watch(self, preferences: UserPreferences) -> Watch:
        watch = Watch(
            watch_id=str(uuid4()),
            status="active",
            preferences=preferences,
        )
        self.watches[watch.watch_id] = watch
        return watch

    def get_watch(self, watch_id: str) -> Optional[Watch]:
        return self.watches.get(watch_id)

    def pause_watch(self, watch_id: str) -> None:
        watch = self.watches[watch_id]
        self.watches[watch_id] = watch.model_copy(update={"status": "paused"})

    def resume_watch(self, watch_id: str) -> None:
        watch = self.watches[watch_id]
        self.watches[watch_id] = watch.model_copy(update={"status": "active"})

    def update_watch(self, watch_id: str, preferences: UserPreferences) -> Watch:
        watch = self.watches[watch_id]
        updated_watch = watch.model_copy(update={"preferences": preferences})
        self.watches[watch_id] = updated_watch
        self.clear_alert_keys(watch_id)
        return updated_watch

    def delete_watch(self, watch_id: str) -> None:
        self.watches.pop(watch_id, None)
        self.alerts = [alert for alert in self.alerts if alert.watch_id != watch_id]
        self.booking_intents = [
            intent for intent in self.booking_intents if intent.watch_id != watch_id
        ]
        self.clear_alert_keys(watch_id)

    def clear_alert_keys(self, watch_id: str) -> None:
        self.alert_keys = {
            alert_key
            for alert_key in self.alert_keys
            if not alert_key.startswith(f"{watch_id}:")
        }

    def mark_watch_checked(self, watch_id: str, checked_at: datetime) -> None:
        watch = self.watches[watch_id]
        self.watches[watch_id] = watch.model_copy(
            update={"last_checked_at": checked_at}
        )

    def add_alert(self, alert: Alert) -> None:
        self.alerts.append(alert)

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        return next(
            (alert for alert in self.alerts if alert.alert_id == alert_id),
            None,
        )

    def update_alert_deliveries(
        self,
        alert_id: str,
        deliveries: list[NotificationDelivery],
    ) -> Alert:
        for index, alert in enumerate(self.alerts):
            if alert.alert_id == alert_id:
                updated_alert = alert.model_copy(update={"deliveries": deliveries})
                self.alerts[index] = updated_alert
                return updated_alert

        raise KeyError(alert_id)

    def list_watches(self) -> list[Watch]:
        return list(self.watches.values())

    def list_alerts(self, watch_id: Optional[str] = None) -> list[Alert]:
        if watch_id is None:
            return self.alerts
        return [alert for alert in self.alerts if alert.watch_id == watch_id]

    def add_check_log(self, log: ReservationCheckLog) -> None:
        self.check_logs.append(log)

    def list_check_logs(
        self,
        watch_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[ReservationCheckLog]:
        logs = self.check_logs
        if watch_id is not None:
            logs = [log for log in logs if log.watch_id == watch_id]

        return sorted(logs, key=lambda log: log.checked_at, reverse=True)[:limit]

    def create_booking_intent(self, booking_intent: BookingIntent) -> BookingIntent:
        existing_intent = self.get_booking_intent_by_alert(booking_intent.alert_id)
        if existing_intent is not None:
            return existing_intent

        self.booking_intents.append(booking_intent)
        return booking_intent

    def get_booking_intent(self, booking_intent_id: str) -> Optional[BookingIntent]:
        return next(
            (
                intent
                for intent in self.booking_intents
                if intent.booking_intent_id == booking_intent_id
            ),
            None,
        )

    def get_booking_intent_by_alert(self, alert_id: str) -> Optional[BookingIntent]:
        return next(
            (intent for intent in self.booking_intents if intent.alert_id == alert_id),
            None,
        )

    def update_booking_intent_status(
        self,
        booking_intent_id: str,
        status: BookingIntentStatus,
        updated_at: datetime,
    ) -> BookingIntent:
        for index, intent in enumerate(self.booking_intents):
            if intent.booking_intent_id == booking_intent_id:
                updated_intent = intent.model_copy(
                    update={
                        "status": status,
                        "updated_at": updated_at,
                    }
                )
                self.booking_intents[index] = updated_intent
                return updated_intent

        raise KeyError(booking_intent_id)

    def list_booking_intents(
        self,
        alert_id: Optional[str] = None,
        watch_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[BookingIntent]:
        intents = self.booking_intents
        if alert_id is not None:
            intents = [intent for intent in intents if intent.alert_id == alert_id]
        if watch_id is not None:
            intents = [intent for intent in intents if intent.watch_id == watch_id]

        return sorted(
            intents,
            key=lambda intent: intent.updated_at,
            reverse=True,
        )[:limit]

    def has_alerted(self, watch_id: str, result: AvailabilityResult) -> bool:
        return self._alert_key(watch_id, result) in self.alert_keys

    def mark_alerted(self, watch_id: str, result: AvailabilityResult) -> None:
        self.alert_keys.add(self._alert_key(watch_id, result))

    def _alert_key(self, watch_id: str, result: AvailabilityResult) -> str:
        return ":".join(
            [
                watch_id,
                result.facility_id,
                result.campsite_id,
                result.available_date.isoformat(),
                result.available_end_date.isoformat(),
            ]
        )


memory_store = MemoryStore()
