CREATE TABLE user_preferences (
    user_id TEXT NOT NULL,
    park_name TEXT NOT NULL,
    date_start DATE NOT NULL,
    date_end DATE NOT NULL,
    camp_type TEXT NOT NULL,
    flexibility_days INTEGER NOT NULL DEFAULT 0,
    notification_type TEXT NOT NULL
);

CREATE TABLE reservation_logs (
    id BIGSERIAL PRIMARY KEY,
    park TEXT NOT NULL,
    availability BOOLEAN NOT NULL,
    date_found TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    price NUMERIC(10, 2),
    success BOOLEAN NOT NULL DEFAULT FALSE
);
