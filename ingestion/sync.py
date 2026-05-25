"""
Data sync orchestrator.

Handles writing parsed game data into the PostgreSQL database.
Supports both daily incremental sync and historical backfill.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.database import SyncSessionLocal
from app.models.at_bat import AtBat
from app.models.game import Game
from app.models.park import Park
from app.models.pitch import Pitch
from app.models.player import Player
from app.models.steal_attempt import StealAttempt
from app.models.team import Team
from ingestion.mlb_client import MLBClient
from ingestion.parsers import ParsedGame, ParsedPlayerRef, parse_game_feed

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Upsert helpers (sync, using psycopg2 driver)
# ---------------------------------------------------------------------------


def _upsert_player(session: Session, ref: ParsedPlayerRef) -> None:
    """Insert or update a player reference."""
    stmt = pg_insert(Player.__table__).values(
        mlb_id=ref.mlb_id,
        first_name=ref.first_name or "",
        last_name=ref.last_name or "",
        full_name=ref.full_name,
        bat_side=ref.bat_side,
        pitch_hand=ref.pitch_hand,
        primary_position=ref.primary_position,
        active=True,
    ).on_conflict_do_update(
        index_elements=["mlb_id"],
        set_={
            "full_name": ref.full_name,
            "first_name": ref.first_name or "",
            "last_name": ref.last_name or "",
            "bat_side": ref.bat_side,
            "pitch_hand": ref.pitch_hand,
            "primary_position": ref.primary_position,
        },
    )
    session.execute(stmt)


def _upsert_game(session: Session, pg: ParsedGame) -> None:
    """Insert or update a game record."""
    stmt = pg_insert(Game.__table__).values(
        mlb_game_id=pg.game_mlb_id,
        game_date=pg.game_date,
        game_datetime=pg.game_datetime,
        season=pg.season,
        game_type=pg.game_type,
        status=pg.status,
        day_night=pg.day_night,
        home_team_mlb_id=pg.home_team_mlb_id,
        away_team_mlb_id=pg.away_team_mlb_id,
        home_score=pg.home_score,
        away_score=pg.away_score,
        park_mlb_id=pg.park_mlb_id,
        double_header=pg.double_header,
        game_number=pg.game_number,
        innings_played=pg.innings_played,
        home_plate_umpire_mlb_id=pg.home_plate_umpire_mlb_id,
    ).on_conflict_do_update(
        index_elements=["mlb_game_id"],
        set_={
            "status": pg.status,
            "home_score": pg.home_score,
            "away_score": pg.away_score,
            "innings_played": pg.innings_played,
            "home_plate_umpire_mlb_id": pg.home_plate_umpire_mlb_id,
        },
    )
    session.execute(stmt)


def _insert_at_bats_and_pitches(session: Session, pg: ParsedGame) -> None:
    """Insert at-bats and their associated pitches."""
    for ab in pg.at_bats:
        # Use INSERT ... ON CONFLICT DO NOTHING to avoid duplicates
        stmt = pg_insert(AtBat.__table__).values(**ab.to_dict()).on_conflict_do_nothing(
            index_elements=["game_mlb_id", "at_bat_number"]
        ).returning(AtBat.id)

        result = session.execute(stmt)
        row = result.fetchone()

        if row is None:
            # Already existed — skip pitches too (idempotent)
            continue

        at_bat_db_id = row[0]

        # Insert pitches for this at-bat
        pitches = pg.pitches.get(ab.at_bat_number, [])
        for p in pitches:
            pitch_stmt = pg_insert(Pitch.__table__).values(
                at_bat_id=at_bat_db_id,
                pitch_number=p.pitch_number,
                pitch_type=p.pitch_type,
                pitch_type_description=p.pitch_type_description,
                pitch_result=p.pitch_result,
                pitch_result_description=p.pitch_result_description,
            ).on_conflict_do_nothing(
                index_elements=["at_bat_id", "pitch_number"]
            )
            session.execute(pitch_stmt)


def _insert_steal_attempts(session: Session, pg: ParsedGame) -> None:
    """Insert steal attempts for a game."""
    session.execute(
        delete(StealAttempt).where(StealAttempt.game_mlb_id == pg.game_mlb_id)
    )
    for steal in pg.steal_attempts:
        session.execute(
            pg_insert(StealAttempt.__table__).values(**steal.to_dict())
        )


def save_parsed_game(pg: ParsedGame) -> None:
    """
    Save all data from a parsed game into the database.

    This is the main entry point for writing game data. It handles
    player upserts, game upsert, at-bat + pitch inserts, and steal inserts
    within a single transaction.
    """
    session = SyncSessionLocal()
    try:
        # 1. Upsert all player references encountered in this game
        for ref in pg.player_refs.values():
            _upsert_player(session, ref)

        # 2. Upsert the game record
        _upsert_game(session, pg)

        # 3. Insert at-bats and pitches
        _insert_at_bats_and_pitches(session, pg)

        # 4. Insert steal attempts
        _insert_steal_attempts(session, pg)

        session.commit()
        logger.info(
            "Saved game %s (%s): %d at-bats, %d steals",
            pg.game_mlb_id,
            pg.game_date,
            len(pg.at_bats),
            len(pg.steal_attempts),
        )
    except Exception:
        session.rollback()
        logger.exception("Failed to save game %s", pg.game_mlb_id)
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Sync orchestration
# ---------------------------------------------------------------------------


async def sync_teams(client: MLBClient, season: int | None = None) -> None:
    """Fetch and upsert all MLB teams."""
    teams = await client.get_teams(season=season)
    session = SyncSessionLocal()
    try:
        for t in teams:
            venue = t.get("venue", {})
            # Upsert park first
            if venue.get("id"):
                park_stmt = pg_insert(Park.__table__).values(
                    mlb_id=venue["id"],
                    name=venue.get("name", "Unknown"),
                ).on_conflict_do_update(
                    index_elements=["mlb_id"],
                    set_={"name": venue.get("name", "Unknown")},
                )
                session.execute(park_stmt)

            # Upsert team
            league = t.get("league", {})
            division = t.get("division", {})
            stmt = pg_insert(Team.__table__).values(
                mlb_id=t["id"],
                name=t.get("name", ""),
                team_name=t.get("teamName", ""),
                abbreviation=t.get("abbreviation", ""),
                league_name=league.get("name"),
                division_name=division.get("name"),
                venue_mlb_id=venue.get("id"),
                active=t.get("active", True),
            ).on_conflict_do_update(
                index_elements=["mlb_id"],
                set_={
                    "name": t.get("name", ""),
                    "team_name": t.get("teamName", ""),
                    "abbreviation": t.get("abbreviation", ""),
                    "league_name": league.get("name"),
                    "division_name": division.get("name"),
                    "venue_mlb_id": venue.get("id"),
                    "active": t.get("active", True),
                },
            )
            session.execute(stmt)
        session.commit()
        logger.info("Synced %d teams", len(teams))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def sync_date(client: MLBClient, target_date: date) -> int:
    """
    Sync all completed games for a single date.

    Returns the number of games processed.
    """
    games = await client.get_schedule(start_date=target_date, end_date=target_date)
    count = 0

    for game_entry in games:
        game_pk = game_entry.get("gamePk")
        status = game_entry.get("status", {}).get("abstractGameState", "")

        if status != "Final":
            logger.debug("Skipping game %s (status: %s)", game_pk, status)
            continue

        try:
            feed = await client.get_game_feed(game_pk)
            parsed = parse_game_feed(feed)
            save_parsed_game(parsed)
            count += 1
        except Exception:
            logger.exception("Error processing game %s on %s", game_pk, target_date)
            continue

    logger.info("Synced %d games for %s", count, target_date)
    return count


async def sync_date_range(
    client: MLBClient,
    start_date: date,
    end_date: date,
    delay: float = 0.5,
) -> int:
    """
    Sync all games across a date range.

    Parameters
    ----------
    delay : float
        Seconds to wait between dates to be polite to the MLB API.

    Returns
    -------
    int
        Total games processed.
    """
    total = 0
    current = start_date
    while current <= end_date:
        count = await sync_date(client, current)
        total += count
        current += timedelta(days=1)
        if delay > 0:
            await asyncio.sleep(delay)
    return total
