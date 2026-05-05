from typing import Any, Callable, Coroutine, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.settings import settings
from app.schemas.reservations import WatchPriority

scheduler = AsyncIOScheduler()
MIN_HIGH_PRIORITY_INTERVAL_SECONDS = 30
LOW_PRIORITY_MULTIPLIER = 5


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def schedule_watch_job(
    watch_id: str,
    check_watch: Callable[[str], Coroutine[Any, Any, object]],
    priority: WatchPriority = "normal",
) -> None:
    scheduler.add_job(
        func=check_watch,
        args=[watch_id],
        trigger="interval",
        seconds=watch_check_interval_seconds(priority),
        id=f"watch:{watch_id}",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def watch_check_interval_seconds(priority: WatchPriority = "normal") -> int:
    base_interval_seconds = max(1, settings.poll_interval_seconds)

    if priority == "high":
        return max(MIN_HIGH_PRIORITY_INTERVAL_SECONDS, base_interval_seconds // 2)
    if priority == "low":
        return base_interval_seconds * LOW_PRIORITY_MULTIPLIER
    return base_interval_seconds


def pause_watch_job(watch_id: str) -> None:
    job_id = f"watch:{watch_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def list_scheduler_jobs() -> list[dict[str, Optional[str]]]:
    return [
        {
            "job_id": job.id,
            "next_run_time": (
                job.next_run_time.isoformat() if job.next_run_time else None
            ),
        }
        for job in scheduler.get_jobs()
    ]
