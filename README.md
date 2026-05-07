# ParkReserve AI

[![CI](https://github.com/srs312-lab/parkreserve-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/srs312-lab/parkreserve-ai/actions/workflows/ci.yml)

Autonomous campground reservation monitoring for U.S. national parks and Recreation.gov facilities.

**Live demo:** [parkreserve-ai-dashboard.vercel.app/demo](https://parkreserve-ai-dashboard.vercel.app/demo)

**Repository:** [github.com/srs312-lab/parkreserve-ai](https://github.com/srs312-lab/parkreserve-ai)

ParkReserve AI lets a user search parks and campgrounds, create one or many reservation watches, continuously poll real Recreation.gov availability, and send email/SMS alerts when matching openings appear. It is built as a portfolio-ready agent system with a FastAPI backend, a Next.js dashboard, Postgres persistence, scheduled background checks, and notification integrations.

The public demo uses static sample data and disabled controls. The real production dashboard is password protected, and backend API routes are protected by a shared server-side token.

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
- Surface watch analytics for hottest campgrounds and latest openings.
- Protect the deployed dashboard with a password gate and shared backend API token.
- Provide a public read-only demo dashboard with sample data at `/demo`.
- Persist watches, alerts, and dedupe keys in Postgres.

## Screenshots

### Public Demo

![Public ParkReserve AI demo dashboard with sample watch analytics](docs/screenshots/public-demo.png)

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
    PublicDemo["Public Demo Route<br/>Static Sample Data"]
    Dashboard["Protected Next.js Dashboard"]
    Proxy["Vercel API Proxy<br/>Injects Server Token"]
    API["Railway FastAPI Backend<br/>Token-Protected Routes"]
    Agent["Reservation Agent Layer"]
    Search["Search Agent"]
    Preference["Preference Agent"]
    Decision["Decision / Ranking Agent"]
    Execution["Execution Agent"]
    Recreation["Recreation.gov"]
    Scheduler["APScheduler"]
    Database["PostgreSQL"]
    Email["Resend Email API"]
    SMS["Twilio SMS"]

    User --> PublicDemo
    User --> Dashboard
    Dashboard --> Proxy
    Proxy --> API
    API --> Agent
    API --> Scheduler
    API --> Database
    Agent --> Preference
    Agent --> Search
    Search --> Recreation
    Agent --> Decision
    Decision --> Execution
    Scheduler --> Agent
    Execution --> Email
    Execution --> SMS
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

Open the safe public demo:

```text
http://127.0.0.1:3001/demo
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

Security:

```text
PARKRESERVE_API_AUTH_TOKEN=generate_a_long_random_shared_token
```

When this token is set on the backend, every backend route except `/health` requires the `X-Parkreserve-Token` header. Keep it unset for simple local development, or route local dashboard requests through the Next.js proxy with the same token.

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

| Surface | URL | Access |
| --- | --- | --- |
| Public demo | `https://parkreserve-ai-dashboard.vercel.app/demo` | Open, static sample data |
| Private dashboard | `https://parkreserve-ai-dashboard.vercel.app/` | HTTP Basic Auth |
| Backend health | `https://parkreserve-ai-production.up.railway.app/health` | Public health check |
| Backend API | Railway service routes | Requires `X-Parkreserve-Token` |

### Backend On Railway

Railway uses [railway.json](railway.json) with [backend/Dockerfile](backend/Dockerfile). Add a Railway Postgres database, then set backend environment variables from [config/production.env.example](config/production.env.example).

Required production values:

```text
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://...
CORS_ORIGINS=https://your-parkreserve-dashboard.vercel.app
PARKRESERVE_API_AUTH_TOKEN=...
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

The dashboard includes [frontend/dashboard/vercel.json](frontend/dashboard/vercel.json). Set these Vercel environment variables:

```text
PARKRESERVE_API_PROXY_TARGET=https://your-parkreserve-api.up.railway.app
PARKRESERVE_API_AUTH_TOKEN=the_same_value_as_railway
DASHBOARD_USERNAME=parkreserve
DASHBOARD_PASSWORD=generate_a_long_random_dashboard_password
```

`DASHBOARD_PASSWORD` enables HTTP Basic Auth for the dashboard and its same-origin API proxy. `PARKRESERVE_API_AUTH_TOKEN` lets the Vercel proxy call the protected Railway backend without exposing the token in browser JavaScript.

After Vercel gives you the dashboard URL, add that exact URL to the backend `CORS_ORIGINS` value and redeploy the backend.

The public demo route is:

```text
https://your-parkreserve-dashboard.vercel.app/demo
```

It uses static sample data and keeps real backend calls, watches, and notification actions out of the public view.

## Production Readiness

- Public demo is isolated from real watches and real notification actions.
- Private dashboard uses HTTP Basic Auth through Next.js middleware.
- Railway backend requires `X-Parkreserve-Token` for every route except `/health`.
- Vercel API proxy injects the backend token server-side, so browser JavaScript never sees it.
- Scheduler uses per-watch priority intervals instead of forcing every watch to poll aggressively.
- Alert deduplication prevents repeated notifications for the same campsite/date opening.
- Delivery records track email/SMS success and support retry for failed channels.
- Auto-booking is intentionally not implemented; the product alerts users without completing purchases.

## Demo Flow

For a portfolio recording or live walkthrough, use the full script in [docs/demo-script.md](docs/demo-script.md).

1. Open the public demo at `/demo` and explain that it is safe, static sample data.
2. Show the protected production dashboard or local dashboard for real controls.
3. Confirm `/settings/status` shows `PostgresStore`, API auth, and configured alert channels.
4. Search for `Yosemite`.
5. Select Upper Pines, Lower Pines, and North Pines.
6. Use a future date window, for example `2026-05-10` to `2026-05-13`.
7. Set `min_nights` to `1` or `2` depending on whether shorter openings should trigger alerts.
8. Choose `high`, `normal`, or `low` priority depending on how aggressively the watch should poll.
9. Choose `both` for email and SMS.
10. Create the batch watch.
11. Use group-level check now to trigger an immediate Recreation.gov lookup.
12. Open next-available dates to show fallback inventory discovery.
13. Pause, resume, edit, or delete a group to demonstrate operational controls.

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
- Add richer trend charts for alert volume and campground demand.
- Add a portfolio case study page with product decisions and screenshots.

## Resume Bullet

Built an autonomous reservation-monitoring platform that scans live Recreation.gov campground inventory, persists user watches in PostgreSQL, schedules recurring availability checks, deduplicates openings, and triggers Resend/Twilio alerts through an agent-based FastAPI and Next.js workflow.
