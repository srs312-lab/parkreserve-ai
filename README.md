# ParkReserve AI

[![CI](https://github.com/srs312-lab/parkreserve-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/srs312-lab/parkreserve-ai/actions/workflows/ci.yml)

Autonomous campground reservation monitoring for U.S. national parks and Recreation.gov facilities.

ParkReserve AI lets a user search parks and campgrounds, create one or many reservation watches, continuously poll real Recreation.gov availability, and send email/SMS alerts when matching openings appear. It is built as a portfolio-ready agent system with a FastAPI backend, a Next.js dashboard, Postgres persistence, scheduled background checks, and notification integrations.

## Why This Exists

Popular national park reservations disappear quickly, especially for Yosemite, Zion, Glacier, Yellowstone, Rocky Mountain, and Grand Canyon. ParkReserve AI turns that painful refresh-loop into an automated workflow:

```text
User preference -> Watch creation -> Scheduled availability checks -> Match ranking -> Alert delivery
```

The current product scope focuses on Recreation.gov campground inventory. The architecture is intentionally set up to expand into lodges, timed-entry permits, lotteries, and private reservation systems later.

## Product Highlights

- Search national parks and campgrounds as you type.
- Create single watches or batch watches for multiple campgrounds.
- Monitor real Recreation.gov campground-month availability.
- Alert on full stays or shorter openings inside a wider date range with `min_nights`.
- Group related watches by park, date window, stay length, site type, and alert channel.
- Pause, resume, edit, check, and delete individual watches or whole groups.
- Show last checked time, next scheduled check, backend poll interval, and dashboard refresh interval.
- Find upcoming available date windows for a watch.
- Send email, SMS, or both through Resend and Twilio.
- Override email and phone recipients per watch when needed.
- Track delivery success rate and filter alerts that need retry.
- Persist watches, alerts, and dedupe keys in Postgres.

## Screenshots

### Dashboard

![ParkReserve AI dashboard with grouped Yosemite watches](docs/screenshots/dashboard.png)

### Batch Watch Creation

![Batch campground search and watch creation flow](docs/screenshots/batch-create.png)

### Next Available Dates

![Next available date results for grouped campground watches](docs/screenshots/next-available.png)

## Architecture

```mermaid
flowchart TD
    User["User"]
    Dashboard["Next.js Dashboard"]
    API["FastAPI Backend"]
    Agent["Reservation Agent Layer"]
    Search["Search Agent"]
    Preference["Preference Agent"]
    Decision["Decision / Ranking Agent"]
    Execution["Execution Agent"]
    Recreation["Recreation.gov"]
    Scheduler["APScheduler"]
    Database["PostgreSQL"]
    Notify["Resend / Twilio"]

    User --> Dashboard
    Dashboard --> API
    API --> Agent
    API --> Scheduler
    Agent --> Preference
    Agent --> Search
    Search --> Recreation
    Agent --> Decision
    Decision --> Execution
    Execution --> Notify
    API --> Database
    Scheduler --> Agent
```

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Lucide icons |
| Backend | FastAPI, Pydantic |
| Availability collector | Recreation.gov HTTP endpoints |
| Scheduler | APScheduler |
| Persistence | PostgreSQL with SQLAlchemy/psycopg |
| Notifications | Resend Email API, Twilio SMS |
| Local dev | Uvicorn, Next dev server |

## Repository Layout

```text
backend/
  app/
    agents/
    api/
    config/
    db/
    notifier/
    ranking_engine/
    reservation_checker/
    scheduler/
    schemas/
frontend/
  dashboard/
config/
  example.env
  production.env.example
.github/
  workflows/
```

## Quickstart

Create a local environment file from the safe example:

```bash
cp config/example.env .env
```

Edit `.env` with your local Postgres URL and optional alert credentials. Keep real secrets in `.env` only; `.env` is ignored by git.

Start the backend from the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

Start the dashboard:

```bash
cd frontend/dashboard
npm install
cp .env.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3001
```

Open the dashboard:

```text
http://127.0.0.1:3001
```

## Environment Variables

`config/example.env` contains placeholders for local setup.

Common local Postgres formats:

```text
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/postgres
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/parkreserve
```

Allowed frontend origins:

```text
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
```

Background polling:

```text
POLL_INTERVAL_SECONDS=60
```

This is the normal-priority availability check interval. High-priority watches check every 30 seconds, normal-priority watches check every 60 seconds, and low-priority watches check every 5 minutes. The dashboard auto-refresh interval is separate and currently configured in `frontend/dashboard/app/page.tsx`.

Email alerts:

```text
EMAIL_PROVIDER=resend
DEFAULT_ALERT_EMAIL=you@example.com
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL="ParkReserve AI <alerts@yourdomain.com>"
```

Resend sends through HTTPS, which works on Railway without SMTP port access. SMTP is still available for local/dev fallback by setting `EMAIL_PROVIDER=smtp` and providing `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL`.

SMS alerts:

```text
DEFAULT_ALERT_PHONE=+15551234567
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_PHONE=+15557654321
```

Optional Recreation Information Database search:

```text
RIDB_API_KEY=your_ridb_api_key
```

## Deployment

The repo includes deployment-ready config for a Vercel dashboard and Railway FastAPI backend.

### Backend On Railway

Railway uses [railway.json](railway.json) with [backend/Dockerfile](backend/Dockerfile). Add a Railway Postgres database, then set backend environment variables from [config/production.env.example](config/production.env.example).

Required production values:

```text
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://...
CORS_ORIGINS=https://your-parkreserve-dashboard.vercel.app
POLL_INTERVAL_SECONDS=60
```

Optional alert/search integrations:

```text
RIDB_API_KEY=...
DEFAULT_ALERT_EMAIL=...
DEFAULT_ALERT_PHONE=...
EMAIL_PROVIDER=resend
RESEND_API_KEY=...
RESEND_FROM_EMAIL=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_PHONE=...
```

The backend health check is:

```text
GET /health
```

### Frontend On Vercel

Create a Vercel project with root directory:

```text
frontend/dashboard
```

The dashboard includes [frontend/dashboard/vercel.json](frontend/dashboard/vercel.json). Set this Vercel environment variable:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-parkreserve-api.up.railway.app
```

After Vercel gives you the dashboard URL, add that exact URL to the backend `CORS_ORIGINS` value and redeploy the backend.

## Demo Flow

For a portfolio recording or live walkthrough, use the full script in [docs/demo-script.md](docs/demo-script.md).

1. Start the backend and dashboard.
2. Confirm `/settings/status` shows `PostgresStore` and configured alert channels.
3. In the dashboard, search for `Yosemite`.
4. Select Upper Pines, Lower Pines, and North Pines.
5. Use a future date window, for example `2026-05-10` to `2026-05-13`.
6. Set `min_nights` to `1` or `2` depending on whether shorter openings should trigger alerts.
7. Choose `high`, `normal`, or `low` priority depending on how aggressively the watch should poll.
8. Choose `both` for email and SMS.
9. Create the batch watch.
10. Use group-level check now to trigger an immediate Recreation.gov lookup.
11. Open next-available dates to show fallback inventory discovery.
12. Pause, resume, edit, or delete a group to demonstrate operational controls.

## API Reference

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/watch-reservation` | Create one watch and schedule polling. |
| `POST` | `/watch-reservations/batch` | Create up to 25 watches and skip duplicates. |
| `GET` | `/availability` | Check live Recreation.gov availability for a facility/date window. |
| `GET` | `/parks/search` | Search supported park names for autocomplete. |
| `GET` | `/campgrounds/search` | Search campground facilities and IDs. |
| `GET` | `/watches` | List active and paused watches. |
| `PATCH` | `/watches/{watch_id}` | Edit dates, site type, minimum nights, alert channel, or priority. |
| `DELETE` | `/watches/{watch_id}` | Delete a watch and its alert history. |
| `POST` | `/pause-agent` | Pause a watch and unschedule its job. |
| `POST` | `/resume-agent` | Resume a watch and reschedule polling. |
| `POST` | `/watches/{watch_id}/check-now` | Run an immediate availability check. |
| `GET` | `/watches/{watch_id}/next-available` | Find upcoming grouped availability windows. |
| `GET` | `/alerts` | List generated alerts, optionally filtered by watch. |
| `POST` | `/alerts/{alert_id}/retry-delivery` | Retry failed or missing alert deliveries. |
| `GET` | `/scheduler/jobs` | Inspect active polling jobs and next run times. |
| `GET` | `/settings/status` | Show safe runtime config and alert integration status. |
| `GET` | `/db/status` | Confirm the active persistence backend. |
| `GET` | `/health` | Health check. |

## Example Requests

Search campgrounds:

```bash
curl "http://127.0.0.1:8000/campgrounds/search?query=Yosemite&limit=5"
```

Check live availability for Upper Pines:

```bash
curl "http://127.0.0.1:8000/availability?park_name=Yosemite%20National%20Park&facility_id=232447&date_start=2026-05-10&date_end=2026-05-13&camp_type=any&min_nights=1"
```

Create a watch with email and SMS alerts:

```bash
curl -X POST "http://127.0.0.1:8000/watch-reservation" \
  -H "Content-Type: application/json" \
  -d '{
    "park_name": "Yosemite National Park",
    "facility_id": "232447",
    "campground_name": "Upper Pines",
    "date_start": "2026-05-10",
    "date_end": "2026-05-13",
    "camp_type": "any",
    "min_nights": 1,
    "flexibility_days": 0,
    "notification_type": "both",
    "priority": "high"
  }'
```

## Data Model

On startup, the backend creates these Postgres tables when needed:

- `reservation_watches`
- `reservation_alerts`
- `reservation_alert_keys`

Alert deduplication uses:

```text
watch_id + facility_id + campsite_id + available_date
```

This prevents repeated notifications for the same campsite opening while still allowing new dates or sites to alert normally.

## Current Scope And Limitations

- Recreation.gov campground availability is supported.
- Auto-booking is intentionally not implemented.
- Resend and Twilio require valid provider credentials.
- Highly competitive dates may return no availability; that still confirms the live source was checked.
- Redis is present in configuration for future queue work, but APScheduler currently runs the polling jobs.

## Roadmap

- Add account login and multi-user watch ownership.
- Add push notifications.
- Add Redis-backed distributed polling.
- Add fallback recommendations across nearby parks and campgrounds.
- Add permit and timed-entry inventory sources.
- Add alert analytics and watch success metrics.
- Deploy a public demo environment.

## Resume Bullet

Built an autonomous reservation-monitoring platform that scans live Recreation.gov campground inventory, persists user watches in PostgreSQL, schedules recurring availability checks, deduplicates openings, and triggers Resend/Twilio alerts through an agent-based FastAPI and Next.js workflow.
