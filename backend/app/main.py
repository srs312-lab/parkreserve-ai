import secrets

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config.settings import settings
from app.db.store import store
from app.scheduler.jobs import start_scheduler, stop_scheduler

app = FastAPI(
    title="ParkReserve AI",
    description="Autonomous national park reservation monitoring agent.",
    version="0.1.0",
)

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    auth_token = (settings.parkreserve_api_auth_token or "").strip()
    if not auth_token or request.method == "OPTIONS" or request.url.path == "/health":
        return await call_next(request)

    request_token = (request.headers.get("x-parkreserve-token") or "").strip()
    if not request_token or not secrets.compare_digest(request_token, auth_token):
        return JSONResponse(
            {"detail": "Missing or invalid API token."},
            status_code=401,
        )

    return await call_next(request)


@app.on_event("startup")
def on_startup() -> None:
    start_scheduler()
    for watch in store.list_watches():
        if watch.status == "active":
            from app.api.routes import agent
            from app.scheduler.jobs import schedule_watch_job

            schedule_watch_job(
                watch.watch_id,
                agent.check_watch,
                watch.preferences.priority,
            )


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
