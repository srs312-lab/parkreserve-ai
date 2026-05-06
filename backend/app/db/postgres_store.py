import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from app.db.memory_store import MemoryStore
from app.schemas.reservations import (
    Alert,
    AvailabilityResult,
    NotificationDelivery,
    UserPreferences,
    Watch,
)


class PostgresStore(MemoryStore):
    def __init__(self, database_url: str) -> None:
        super().__init__()
        self.database_url = _normalize_database_url(database_url)

    def is_available(self) -> bool:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1")
        except Exception:
            return False
        return True

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_watches (
                    watch_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    preferences JSONB NOT NULL,
                    last_checked_at TIMESTAMPTZ
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_alerts (
                    alert_id TEXT PRIMARY KEY,
                    watch_id TEXT NOT NULL REFERENCES reservation_watches(watch_id),
                    park_name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    reservation_url TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    deliveries JSONB NOT NULL DEFAULT '[]'::jsonb
                )
                """
            )
            connection.execute(
                """
                ALTER TABLE reservation_alerts
                    ADD COLUMN IF NOT EXISTS campground_name TEXT,
                    ADD COLUMN IF NOT EXISTS facility_id TEXT,
                    ADD COLUMN IF NOT EXISTS campsite_id TEXT,
                    ADD COLUMN IF NOT EXISTS site TEXT,
                    ADD COLUMN IF NOT EXISTS available_date DATE,
                    ADD COLUMN IF NOT EXISTS available_end_date DATE,
                    ADD COLUMN IF NOT EXISTS nights INTEGER,
                    ADD COLUMN IF NOT EXISTS site_type TEXT
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_alert_keys (
                    alert_key TEXT PRIMARY KEY,
                    watch_id TEXT NOT NULL REFERENCES reservation_watches(watch_id)
                )
                """
            )
            connection.commit()

    def create_watch(self, preferences: UserPreferences) -> Watch:
        watch = Watch(
            watch_id=str(uuid4()),
            status="active",
            preferences=preferences,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reservation_watches (
                    watch_id,
                    status,
                    preferences,
                    last_checked_at
                )
                VALUES (%s, %s, %s::jsonb, %s)
                """,
                (
                    watch.watch_id,
                    watch.status,
                    json.dumps(preferences.model_dump(mode="json")),
                    watch.last_checked_at,
                ),
            )
            connection.commit()
        return watch

    def get_watch(self, watch_id: str) -> Optional[Watch]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT watch_id, status, preferences, last_checked_at
                FROM reservation_watches
                WHERE watch_id = %s
                """,
                (watch_id,),
            ).fetchone()

        if row is None:
            return None
        return self._watch_from_row(row)

    def pause_watch(self, watch_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE reservation_watches
                SET status = 'paused'
                WHERE watch_id = %s
                """,
                (watch_id,),
            )
            connection.commit()

    def resume_watch(self, watch_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE reservation_watches
                SET status = 'active'
                WHERE watch_id = %s
                """,
                (watch_id,),
            )
            connection.commit()

    def update_watch(self, watch_id: str, preferences: UserPreferences) -> Watch:
        with self._connect() as connection:
            row = connection.execute(
                """
                UPDATE reservation_watches
                SET preferences = %s::jsonb
                WHERE watch_id = %s
                RETURNING watch_id, status, preferences, last_checked_at
                """,
                (
                    json.dumps(preferences.model_dump(mode="json")),
                    watch_id,
                ),
            ).fetchone()
            connection.execute(
                "DELETE FROM reservation_alert_keys WHERE watch_id = %s",
                (watch_id,),
            )
            connection.commit()

        return self._watch_from_row(row)

    def delete_watch(self, watch_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM reservation_alert_keys WHERE watch_id = %s",
                (watch_id,),
            )
            connection.execute(
                "DELETE FROM reservation_alerts WHERE watch_id = %s",
                (watch_id,),
            )
            connection.execute(
                "DELETE FROM reservation_watches WHERE watch_id = %s",
                (watch_id,),
            )
            connection.commit()

    def mark_watch_checked(self, watch_id: str, checked_at: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE reservation_watches
                SET last_checked_at = %s
                WHERE watch_id = %s
                """,
                (checked_at, watch_id),
            )
            connection.commit()

    def add_alert(self, alert: Alert) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reservation_alerts (
                    alert_id,
                    watch_id,
                    park_name,
                    message,
                    reservation_url,
                    created_at,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    deliveries
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s::jsonb
                )
                ON CONFLICT (alert_id) DO NOTHING
                """,
                (
                    alert.alert_id,
                    alert.watch_id,
                    alert.park_name,
                    alert.message,
                    alert.reservation_url,
                    alert.created_at,
                    alert.campground_name,
                    alert.facility_id,
                    alert.campsite_id,
                    alert.site,
                    alert.available_date,
                    alert.available_end_date,
                    alert.nights,
                    alert.site_type,
                    json.dumps(
                        [
                            delivery.model_dump(mode="json")
                            for delivery in alert.deliveries
                        ]
                    ),
                ),
            )
            connection.commit()

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    alert_id,
                    watch_id,
                    park_name,
                    message,
                    reservation_url,
                    created_at,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    deliveries
                FROM reservation_alerts
                WHERE alert_id = %s
                """,
                (alert_id,),
            ).fetchone()

        if row is None:
            return None
        return Alert.model_validate(row)

    def update_alert_deliveries(
        self,
        alert_id: str,
        deliveries: list[NotificationDelivery],
    ) -> Alert:
        with self._connect() as connection:
            row = connection.execute(
                """
                UPDATE reservation_alerts
                SET deliveries = %s::jsonb
                WHERE alert_id = %s
                RETURNING
                    alert_id,
                    watch_id,
                    park_name,
                    message,
                    reservation_url,
                    created_at,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    deliveries
                """,
                (
                    json.dumps(
                        [
                            delivery.model_dump(mode="json")
                            for delivery in deliveries
                        ]
                    ),
                    alert_id,
                ),
            ).fetchone()
            connection.commit()

        if row is None:
            raise KeyError(alert_id)
        return Alert.model_validate(row)

    def list_watches(self) -> list[Watch]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT watch_id, status, preferences, last_checked_at
                FROM reservation_watches
                ORDER BY last_checked_at DESC NULLS LAST, watch_id
                """
            ).fetchall()

        return [self._watch_from_row(row) for row in rows]

    def list_alerts(self, watch_id: Optional[str] = None) -> list[Alert]:
        params = ()
        where_clause = ""
        if watch_id is not None:
            where_clause = "WHERE watch_id = %s"
            params = (watch_id,)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    alert_id,
                    watch_id,
                    park_name,
                    message,
                    reservation_url,
                    created_at,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    deliveries
                FROM reservation_alerts
                {where_clause}
                ORDER BY created_at ASC
                """,
                params,
            ).fetchall()

        return [Alert.model_validate(row) for row in rows]

    def has_alerted(self, watch_id: str, result: AvailabilityResult) -> bool:
        alert_key = self._alert_key(watch_id, result)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT alert_key
                FROM reservation_alert_keys
                WHERE alert_key = %s
                """,
                (alert_key,),
            ).fetchone()
        return row is not None

    def mark_alerted(self, watch_id: str, result: AvailabilityResult) -> None:
        alert_key = self._alert_key(watch_id, result)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reservation_alert_keys (alert_key, watch_id)
                VALUES (%s, %s)
                ON CONFLICT (alert_key) DO NOTHING
                """,
                (alert_key, watch_id),
            )
            connection.commit()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _watch_from_row(self, row: dict) -> Watch:
        return Watch(
            watch_id=row["watch_id"],
            status=row["status"],
            preferences=UserPreferences.model_validate(row["preferences"]),
            last_checked_at=row["last_checked_at"],
        )


def _normalize_database_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
