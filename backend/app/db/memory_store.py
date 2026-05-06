from datetime import datetime
from uuid import uuid4
from typing import Optional

from app.schemas.reservations import (
    Alert,
    AvailabilityResult,
    NotificationDelivery,
    UserPreferences,
    Watch,
)


class MemoryStore:
    def __init__(self) -> None:
        self.watches: dict[str, Watch] = {}
        self.alerts: list[Alert] = []
        self.alert_keys: set[str] = set()

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
