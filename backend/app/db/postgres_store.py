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
    BookingIntent,
    BookingIntentStatus,
    NotificationDelivery,
    ReservationCheckLog,
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_check_logs (
                    log_id TEXT PRIMARY KEY,
                    watch_id TEXT NOT NULL REFERENCES reservation_watches(watch_id),
                    checked_at TIMESTAMPTZ NOT NULL,
                    status TEXT NOT NULL,
                    result_count INTEGER NOT NULL DEFAULT 0,
                    alert_created BOOLEAN NOT NULL DEFAULT FALSE,
                    error_message TEXT,
                    top_match_summary TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS booking_intents (
                    booking_intent_id TEXT PRIMARY KEY,
                    alert_id TEXT NOT NULL UNIQUE
                        REFERENCES reservation_alerts(alert_id),
                    watch_id TEXT NOT NULL REFERENCES reservation_watches(watch_id),
                    status TEXT NOT NULL,
                    handoff_url TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    park_name TEXT NOT NULL,
                    campground_name TEXT,
                    facility_id TEXT,
                    campsite_id TEXT,
                    site TEXT,
                    available_date DATE,
                    available_end_date DATE,
                    nights INTEGER,
                    site_type TEXT,
                    note TEXT NOT NULL
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
                "DELETE FROM booking_intents WHERE watch_id = %s",
                (watch_id,),
            )
            connection.execute(
                "DELETE FROM reservation_check_logs WHERE watch_id = %s",
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

    def add_check_log(self, log: ReservationCheckLog) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reservation_check_logs (
                    log_id,
                    watch_id,
                    checked_at,
                    status,
                    result_count,
                    alert_created,
                    error_message,
                    top_match_summary
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (log_id) DO NOTHING
                """,
                (
                    log.log_id,
                    log.watch_id,
                    log.checked_at,
                    log.status,
                    log.result_count,
                    log.alert_created,
                    log.error_message,
                    log.top_match_summary,
                ),
            )
            connection.commit()

    def list_check_logs(
        self,
        watch_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[ReservationCheckLog]:
        params: tuple[object, ...] = (limit,)
        where_clause = ""
        if watch_id is not None:
            where_clause = "WHERE watch_id = %s"
            params = (watch_id, limit)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    log_id,
                    watch_id,
                    checked_at,
                    status,
                    result_count,
                    alert_created,
                    error_message,
                    top_match_summary
                FROM reservation_check_logs
                {where_clause}
                ORDER BY checked_at DESC
                LIMIT %s
                """,
                params,
            ).fetchall()

        return [ReservationCheckLog.model_validate(row) for row in rows]

    def create_booking_intent(self, booking_intent: BookingIntent) -> BookingIntent:
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO booking_intents (
                    booking_intent_id,
                    alert_id,
                    watch_id,
                    status,
                    handoff_url,
                    created_at,
                    updated_at,
                    park_name,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    note
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (alert_id) DO UPDATE
                    SET updated_at = booking_intents.updated_at
                RETURNING
                    booking_intent_id,
                    alert_id,
                    watch_id,
                    status,
                    handoff_url,
                    created_at,
                    updated_at,
                    park_name,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    note
                """,
                (
                    booking_intent.booking_intent_id,
                    booking_intent.alert_id,
                    booking_intent.watch_id,
                    booking_intent.status,
                    booking_intent.handoff_url,
                    booking_intent.created_at,
                    booking_intent.updated_at,
                    booking_intent.park_name,
                    booking_intent.campground_name,
                    booking_intent.facility_id,
                    booking_intent.campsite_id,
                    booking_intent.site,
                    booking_intent.available_date,
                    booking_intent.available_end_date,
                    booking_intent.nights,
                    booking_intent.site_type,
                    booking_intent.note,
                ),
            ).fetchone()
            connection.commit()

        return BookingIntent.model_validate(row)

    def get_booking_intent(self, booking_intent_id: str) -> Optional[BookingIntent]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    booking_intent_id,
                    alert_id,
                    watch_id,
                    status,
                    handoff_url,
                    created_at,
                    updated_at,
                    park_name,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    note
                FROM booking_intents
                WHERE booking_intent_id = %s
                """,
                (booking_intent_id,),
            ).fetchone()

        if row is None:
            return None
        return BookingIntent.model_validate(row)

    def get_booking_intent_by_alert(self, alert_id: str) -> Optional[BookingIntent]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    booking_intent_id,
                    alert_id,
                    watch_id,
                    status,
                    handoff_url,
                    created_at,
                    updated_at,
                    park_name,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    note
                FROM booking_intents
                WHERE alert_id = %s
                """,
                (alert_id,),
            ).fetchone()

        if row is None:
            return None
        return BookingIntent.model_validate(row)

    def update_booking_intent_status(
        self,
        booking_intent_id: str,
        status: BookingIntentStatus,
        updated_at: datetime,
    ) -> BookingIntent:
        with self._connect() as connection:
            row = connection.execute(
                """
                UPDATE booking_intents
                SET status = %s, updated_at = %s
                WHERE booking_intent_id = %s
                RETURNING
                    booking_intent_id,
                    alert_id,
                    watch_id,
                    status,
                    handoff_url,
                    created_at,
                    updated_at,
                    park_name,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    note
                """,
                (status, updated_at, booking_intent_id),
            ).fetchone()
            connection.commit()

        if row is None:
            raise KeyError(booking_intent_id)
        return BookingIntent.model_validate(row)

    def list_booking_intents(
        self,
        alert_id: Optional[str] = None,
        watch_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[BookingIntent]:
        filters = []
        params: list[object] = []
        if alert_id is not None:
            filters.append("alert_id = %s")
            params.append(alert_id)
        if watch_id is not None:
            filters.append("watch_id = %s")
            params.append(watch_id)

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    booking_intent_id,
                    alert_id,
                    watch_id,
                    status,
                    handoff_url,
                    created_at,
                    updated_at,
                    park_name,
                    campground_name,
                    facility_id,
                    campsite_id,
                    site,
                    available_date,
                    available_end_date,
                    nights,
                    site_type,
                    note
                FROM booking_intents
                {where_clause}
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                tuple(params),
            ).fetchall()

        return [BookingIntent.model_validate(row) for row in rows]

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
