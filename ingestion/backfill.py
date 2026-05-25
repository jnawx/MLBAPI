"""
Historical backfill script.

Loads all game data from a specified start year to present.
Run this once to populate the database with historical data.

Usage:
    python -m ingestion.backfill --start-year 2021
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date

from ingestion.mlb_client import MLBClient
from ingestion.sync import sync_date_range, sync_teams

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Approximate MLB season date ranges
SEASON_DATES: dict[int, tuple[str, str]] = {
    2021: ("2021-04-01", "2021-11-03"),
    2022: ("2022-04-07", "2022-11-06"),
    2023: ("2023-03-30", "2023-11-02"),
    2024: ("2024-03-20", "2024-11-03"),
    2025: ("2025-03-27", "2025-10-31"),
    2026: ("2026-03-01", "2026-11-30"),
}


def _season_dates(year: int) -> tuple[date, date]:
    """Return a broad MLB season window for a year."""
    if year in SEASON_DATES:
        start_str, end_str = SEASON_DATES[year]
        return date.fromisoformat(start_str), date.fromisoformat(end_str)
    return date(year, 3, 1), date(year, 11, 30)


async def backfill(start_year: int, end_year: int | None = None) -> None:
    """Run a full backfill from start_year through end_year (inclusive)."""
    today = date.today()
    if end_year is None:
        end_year = today.year

    async with MLBClient() as client:
        # First, sync teams for each season
        for year in range(start_year, end_year + 1):
            logger.info("Syncing teams for %d...", year)
            await sync_teams(client, season=year)

        # Then sync game data season by season
        for year in range(start_year, end_year + 1):
            s_date, configured_end_date = _season_dates(year)
            e_date = min(configured_end_date, today)

            if s_date > today:
                logger.info("Season %d hasn't started yet, skipping", year)
                continue

            logger.info(
                "Backfilling season %d: %s to %s",
                year,
                s_date.isoformat(),
                e_date.isoformat(),
            )

            total = await sync_date_range(client, s_date, e_date, delay=0.3)
            logger.info("Season %d complete: %d games", year, total)


def main():
    parser = argparse.ArgumentParser(description="Backfill MLB game data")
    parser.add_argument(
        "--start-year",
        type=int,
        default=2021,
        help="First season to backfill (default: 2021)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Last season to backfill (default: current year)",
    )
    args = parser.parse_args()

    asyncio.run(backfill(args.start_year, args.end_year))


if __name__ == "__main__":
    main()
