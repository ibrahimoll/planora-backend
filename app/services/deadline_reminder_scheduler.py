from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.deadline_reminder_service import run_deadline_reminder_scan

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task[None] | None = None


def _run_deadline_reminder_scan_once() -> None:
    db: Session = SessionLocal()

    try:
        result = run_deadline_reminder_scan(
            db=db,
            hours_ahead=settings.deadline_reminder_hours_ahead,
            include_overdue=settings.deadline_reminder_include_overdue,
        )
        logger.info("Automatic deadline reminder scan completed: %s", result)
    except Exception:
        db.rollback()
        logger.exception("Automatic deadline reminder scan failed.")
    finally:
        db.close()


async def _deadline_reminder_scheduler_loop() -> None:
    interval_seconds = max(
        settings.deadline_reminder_scheduler_interval_minutes,
        1,
    ) * 60

    while True:
        await asyncio.to_thread(_run_deadline_reminder_scan_once)
        await asyncio.sleep(interval_seconds)


def start_deadline_reminder_scheduler() -> None:
    global _scheduler_task

    if not settings.deadline_reminder_scheduler_enabled:
        return

    if _scheduler_task is not None and not _scheduler_task.done():
        return

    _scheduler_task = asyncio.create_task(_deadline_reminder_scheduler_loop())


async def stop_deadline_reminder_scheduler() -> None:
    global _scheduler_task

    if _scheduler_task is None:
        return

    task = _scheduler_task
    _scheduler_task = None

    task.cancel()

    with suppress(asyncio.CancelledError):
        await task