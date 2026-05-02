from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    start_scheduler()
    for watch in store.list_watches():
        if watch.status == "active":
            from app.api.routes import agent
            from app.scheduler.jobs import schedule_watch_job

            schedule_watch_job(watch.watch_id, agent.check_watch)


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
