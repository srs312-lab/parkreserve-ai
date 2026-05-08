CREATE TABLE IF NOT EXISTS reservation_watches (
    watch_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    preferences JSONB NOT NULL,
    last_checked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS reservation_alerts (
    alert_id TEXT PRIMARY KEY,
    watch_id TEXT NOT NULL REFERENCES reservation_watches(watch_id),
    park_name TEXT NOT NULL,
    message TEXT NOT NULL,
    reservation_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    campground_name TEXT,
    facility_id TEXT,
    campsite_id TEXT,
    site TEXT,
    available_date DATE,
    available_end_date DATE,
    nights INTEGER,
    site_type TEXT,
    deliveries JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS reservation_alert_keys (
    alert_key TEXT PRIMARY KEY,
    watch_id TEXT NOT NULL REFERENCES reservation_watches(watch_id)
);

CREATE TABLE IF NOT EXISTS reservation_check_logs (
    log_id TEXT PRIMARY KEY,
    watch_id TEXT NOT NULL REFERENCES reservation_watches(watch_id),
    checked_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    alert_created BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    top_match_summary TEXT
);

CREATE TABLE IF NOT EXISTS booking_intents (
    booking_intent_id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL UNIQUE REFERENCES reservation_alerts(alert_id),
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
);
