"""
Backfill home plate umpire MLB IDs for all existing games.

Fetches each game feed from the MLB Stats API to extract the
home plate umpire, then writes the ID into the games table.
This is a one-time migration — subsequent syncs will capture
umpires automatically via the updated parser.

Usage
-----
    cd p:\\Projects\\MLBAPI
    python scripts/backfill_umpires.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from app.config import settings
from ingestion.mlb_client import MLBClient


async def main() -> None:
    engine = create_engine(settings.database_url_sync)

    # ── 1. Find games that still need an umpire ID ────────────────
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT mlb_game_id FROM games "
            "WHERE home_plate_umpire_mlb_id IS NULL "
            "  AND status = 'Final' "
            "ORDER BY game_date"
        )).fetchall()

    game_ids = [r[0] for r in rows]
    total = len(game_ids)
    print(f"🏟️  {total:,} games need umpire backfill")

    if not total:
        print("✅  Nothing to do — all games already have umpire data.")
        return

    # ── 2. Fetch each game feed and extract umpire ────────────────
    updated = 0
    skipped = 0
    errors = 0
    batch_size = 50           # commit every N games
    delay = 0.25              # seconds between API calls
    batch_values: list[dict] = []

    async with MLBClient(timeout=20.0) as client:
        for i, game_pk in enumerate(game_ids, 1):
            try:
                feed = await client.get_game_feed(game_pk)
                live_data = feed.get("liveData", {})
                officials = live_data.get("boxscore", {}).get("officials", [])

                hp_ump_id = None
                for official in officials:
                    if official.get("officialType") == "Home Plate":
                        hp_ump_id = official.get("official", {}).get("id")
                        break

                if hp_ump_id:
                    batch_values.append({
                        "game_id": game_pk,
                        "ump_id": hp_ump_id,
                    })
                    updated += 1
                else:
                    skipped += 1

            except Exception as exc:
                errors += 1
                if errors <= 5:
                    print(f"    ⚠️  Error on game {game_pk}: {exc}")

            # Progress + batch commit
            if i % batch_size == 0 or i == total:
                if batch_values:
                    with engine.connect() as conn:
                        conn.execute(
                            text(
                                "UPDATE games SET home_plate_umpire_mlb_id = :ump_id "
                                "WHERE mlb_game_id = :game_id"
                            ),
                            batch_values,
                        )
                        conn.commit()
                    batch_values = []

                elapsed = time.time() - t0
                rate = i / elapsed if elapsed > 0 else 0
                eta = (total - i) / rate if rate > 0 else 0
                print(
                    f"    [{i:>6,}/{total:,}] "
                    f"updated={updated:,}  skipped={skipped:,}  errors={errors:,}  "
                    f"({rate:.1f} games/s, ETA {eta:.0f}s)"
                )

            await asyncio.sleep(delay)

    print(f"\n✅  Done!  {updated:,} games updated, "
          f"{skipped:,} skipped (no umpire data), {errors:,} errors")


if __name__ == "__main__":
    t0 = time.time()
    asyncio.run(main())
    print(f"Total time: {time.time() - t0:.1f}s")
