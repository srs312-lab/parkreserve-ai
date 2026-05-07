# ParkReserve AI Demo Script

Use this as a five-minute walkthrough for a portfolio recording or live demo.

## 1. Public Demo

Start with the public demo at:

```text
https://parkreserve-ai-dashboard.vercel.app/demo
```

Say:

> ParkReserve AI monitors national park campground reservations and sends instant alerts when matching Recreation.gov openings appear.

Point out:

- This route is safe for public viewers.
- It uses static sample data.
- All action buttons are disabled.
- The real dashboard and backend remain protected.

## 2. Product Setup

For a private walkthrough, open the protected dashboard:

```text
http://127.0.0.1:3001
```

Point out:

- Watch creation form.
- Park autocomplete.
- Campground batch selection.
- System status panel.
- Watches grouped by park/date/stay preferences.

## 3. Create A Batch Watch

Search:

```text
Yosemite
```

Select:

```text
Upper Pines
Lower Pines
North Pines
```

Use an example future date range:

```text
2026-05-10 to 2026-05-13
```

Set:

```text
Minimum nights: 1
Alert channel: both
Site type: any
```

Say:

> A single user request becomes multiple scheduled watches, one per campground, with duplicate protection.

## 4. Show Operations

After creating watches, point out:

- Group-level actions: pause, resume, check now, next dates, delete.
- Individual watch actions: edit, pause, resume, next dates, manual check, delete.
- Last checked and next scheduled check timestamps.
- Dashboard auto-refresh countdown.

Say:

> This is not just a scraper. It behaves like an operational agent dashboard.

## 5. Trigger A Manual Check

Use group-level check now.

Say:

> Manual check uses the same Recreation.gov collector as the scheduler, so the user can test immediately instead of waiting for the next background run.

If no availability appears, explain:

> No availability is still a real live result. Popular dates often return empty inventory, which is exactly why the background monitor is useful.

## 6. Show Next Available Dates

Use the calendar/next-available action.

Say:

> The system can look beyond the selected window and surface fallback openings, which is the start of recommendation intelligence.

## 7. Show Alert Infrastructure

Open the system status panel.

Point out:

- Postgres persistence.
- Backend polling interval.
- Email integration.
- SMS integration.
- Recreation.gov source.
- API auth status.
- Delivery health and retry state.

Say:

> Watches and alerts persist in Postgres, scheduler jobs keep running in the background, and notification delivery is handled through Resend and Twilio.

## 8. Security And Deployment

Say:

> The public demo is separate from the real app. Production dashboard access is password protected, and Vercel proxies API requests with a server-side token so the Railway backend is not publicly writable.

Point out:

- Vercel dashboard and `/demo` route.
- Railway FastAPI backend.
- Token-protected backend routes.
- Public `/health` endpoint.
- GitHub Actions CI.

## 9. Architecture Close

End with:

> The architecture is designed to grow from campground monitoring into a broader reservation agent: more parks, more inventory sources, smarter fallback ranking, and eventually account-based SaaS workflows.

Resume bullet:

```text
Built an autonomous reservation-monitoring platform that scans live Recreation.gov campground inventory, persists user watches in PostgreSQL, schedules recurring availability checks, deduplicates openings, and triggers Resend/Twilio alerts through an agent-based FastAPI and Next.js workflow.
```
