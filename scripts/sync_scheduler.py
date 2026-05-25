"""Long-running daily sync scheduler for container deployments."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from ingestion.mlb_client import MLBClient
from ingestion.sync import sync_date, sync_teams

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid %s=%r, using %d", name, value, default)
        return default


def _parse_sync_time(value: str) -> time:
    try:
        hour_str, minute_str = value.split(":", 1)
        return time(hour=int(hour_str), minute=int(minute_str))
    except (ValueError, TypeError):
        logger.warning("Invalid DAILY_SYNC_TIME=%r, using 06:00", value)
        return time(hour=6, minute=0)


def _seconds_until_next_run(now: datetime, run_time: time) -> float:
    next_run = now.replace(
        hour=run_time.hour,
        minute=run_time.minute,
        second=0,
        microsecond=0,
    )
    if next_run <= now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


async def _run_sync(days_ago: int, tz: ZoneInfo) -> None:
    target_date = datetime.now(tz).date() - timedelta(days=days_ago)
    logger.info("Starting MLB daily sync for %s", target_date.isoformat())

    async with MLBClient() as client:
        await sync_teams(client)
        count = await sync_date(client, target_date)

    logger.info("MLB daily sync complete for %s: %d games", target_date.isoformat(), count)


async def _run_with_retries(days_ago: int, tz: ZoneInfo, retry_seconds: int) -> None:
    while True:
        try:
            await _run_sync(days_ago, tz)
            return
        except Exception:
            logger.exception("Sync failed; retrying in %d seconds", retry_seconds)
            await asyncio.sleep(retry_seconds)


async def main() -> None:
    tz_name = os.getenv("TZ", "America/Phoenix")
    tz = ZoneInfo(tz_name)
    run_time = _parse_sync_time(os.getenv("DAILY_SYNC_TIME", "06:00"))
    days_ago = _env_int("SYNC_TARGET_DAYS_AGO", 1)
    retry_seconds = _env_int("SYNC_RETRY_SECONDS", 3600)

    logger.info(
        "Scheduler ready: daily sync at %s %s, target=%d day(s) ago",
        run_time.strftime("%H:%M"),
        tz_name,
        days_ago,
    )

    if _env_bool("SYNC_ON_START", True):
        await _run_with_retries(days_ago, tz, retry_seconds)

    while True:
        now = datetime.now(tz)
        sleep_seconds = _seconds_until_next_run(now, run_time)
        next_run = now + timedelta(seconds=sleep_seconds)
        logger.info("Next MLB daily sync scheduled for %s", next_run.isoformat())
        await asyncio.sleep(sleep_seconds)

        await _run_with_retries(days_ago, tz, retry_seconds)


if __name__ == "__main__":
    asyncio.run(main())
