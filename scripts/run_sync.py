"""
Daily sync script — fetch and store yesterday's completed games.

Usage:
    python -m scripts.run_sync
    python -m scripts.run_sync --date 2024-07-15
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, timedelta

from ingestion.mlb_client import MLBClient
from ingestion.sync import sync_date, sync_teams

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def daily_sync(target: date | None = None) -> None:
    """Sync a single day's games. Defaults to yesterday."""
    if target is None:
        target = date.today() - timedelta(days=1)

    async with MLBClient() as client:
        # Refresh teams (quick, ensures mid-season changes are captured)
        await sync_teams(client)

        count = await sync_date(client, target)
        logger.info("Daily sync complete for %s: %d games processed", target, count)


def main():
    parser = argparse.ArgumentParser(description="Daily MLB data sync")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to sync (YYYY-MM-DD). Defaults to yesterday.",
    )
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else None
    asyncio.run(daily_sync(target))


if __name__ == "__main__":
    main()
