"""
Pydantic schemas for the stats query API.

These define the filter parameters users can pass and the shape of the response.
"""

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Filter parameters (used as query-param models in the API)
# ---------------------------------------------------------------------------


class BattingStatsRequest(BaseModel):
    """Filter parameters for a batting stats query."""

    # ── Who ────────────────────────────────────────────────────────────
    batter_ids: Optional[list[int]] = Field(None, description="MLB player IDs for batters")
    batter_team_ids: Optional[list[int]] = Field(None, description="MLB team IDs (team the batter played for)")
    pitcher_ids: Optional[list[int]] = Field(None, description="Filter by opposing pitcher MLB IDs")
    pitcher_team_ids: Optional[list[int]] = Field(None, description="Filter by opposing pitcher's team")

    # ── When ───────────────────────────────────────────────────────────
    seasons: Optional[list[int]] = Field(None, description="Seasons (e.g. [2023, 2024])")
    date_from: Optional[date] = Field(None, description="Start date (inclusive)")
    date_to: Optional[date] = Field(None, description="End date (inclusive)")
    months: Optional[list[int]] = Field(None, description="Calendar months (1–12)")
    game_type: Optional[str] = Field("R", description="R=regular, P=postseason, S=spring, A=allstar")

    # ── Splits ─────────────────────────────────────────────────────────
    bat_side: Optional[str] = Field(None, description="Batter handedness this at-bat: L or R")
    pitch_hand: Optional[str] = Field(None, description="Pitcher handedness: L or R")
    home_away: Optional[str] = Field(None, description="'home' or 'away'")

    # ── Situation ──────────────────────────────────────────────────────
    batting_order_positions: Optional[list[int]] = Field(None, description="Lineup spot (1–9)")
    innings: Optional[list[int]] = Field(None, description="Inning numbers")
    min_inning: Optional[int] = Field(None, description="Minimum inning (inclusive)")
    max_inning: Optional[int] = Field(None, description="Maximum inning (inclusive)")
    outs: Optional[list[int]] = Field(None, description="Outs before the at-bat (0, 1, 2)")
    runners_on: Optional[str] = Field(
        None,
        description=(
            "Runner situation: 'empty', 'on_base', 'risp', 'loaded', "
            "'1b', '2b', '3b', '1b_2b', '1b_3b', '2b_3b'"
        ),
    )

    # ── Score ──────────────────────────────────────────────────────────
    score_diff_min: Optional[int] = Field(None, description="Min score diff (batting - fielding). Negative = trailing")
    score_diff_max: Optional[int] = Field(None, description="Max score diff")

    # ── Count ──────────────────────────────────────────────────────────
    balls: Optional[list[int]] = Field(None, description="Ball count before final pitch (0–3)")
    strikes: Optional[list[int]] = Field(None, description="Strike count before final pitch (0–2)")

    # ── Park ───────────────────────────────────────────────────────────
    park_ids: Optional[list[int]] = Field(None, description="MLB venue IDs")

    # ── Statcast filters ──────────────────────────────────────────────
    min_exit_velocity: Optional[float] = Field(None, description="Min exit velocity (mph)")
    max_exit_velocity: Optional[float] = Field(None, description="Max exit velocity (mph)")
    min_launch_angle: Optional[float] = Field(None, description="Min launch angle (degrees)")
    max_launch_angle: Optional[float] = Field(None, description="Max launch angle (degrees)")

    # ── Grouping & Pagination ─────────────────────────────────────────
    group_by: Optional[list[str]] = Field(
        default=["batter"],
        description=(
            "Group results by: 'batter', 'pitcher', 'batter_team', 'pitcher_team', "
            "'season', 'month', 'park', 'bat_side', 'pitch_hand', "
            "'batting_order_position', 'inning', 'home_away', 'league'"
        ),
    )
    min_pa: Optional[int] = Field(None, description="Minimum plate appearances to include in results")
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)
    sort_by: Optional[str] = Field(None, description="Stat field to sort by")
    sort_dir: Optional[str] = Field("desc", description="'asc' or 'desc'")


class PitchingStatsRequest(BaseModel):
    """Filter parameters for a pitching stats query (same at-bat data, pitcher perspective)."""

    # ── Who ────────────────────────────────────────────────────────────
    pitcher_ids: Optional[list[int]] = Field(None, description="MLB pitcher IDs")
    pitcher_team_ids: Optional[list[int]] = Field(None, description="Team the pitcher played for")
    batter_ids: Optional[list[int]] = Field(None, description="Filter by opposing batter MLB IDs")
    batter_team_ids: Optional[list[int]] = Field(None, description="Filter by opposing batter's team")

    # ── When ───────────────────────────────────────────────────────────
    seasons: Optional[list[int]] = Field(None, description="Seasons")
    date_from: Optional[date] = Field(None, description="Start date (inclusive)")
    date_to: Optional[date] = Field(None, description="End date (inclusive)")
    months: Optional[list[int]] = Field(None, description="Calendar months")
    game_type: Optional[str] = Field("R", description="Game type filter")

    # ── Splits ─────────────────────────────────────────────────────────
    pitch_hand: Optional[str] = Field(None, description="Pitcher handedness: L or R")
    vs_bat_side: Optional[str] = Field(None, description="Opposing batter handedness: L or R")
    home_away: Optional[str] = Field(None, description="'home' or 'away' (pitcher's perspective)")

    # ── Situation ──────────────────────────────────────────────────────
    innings: Optional[list[int]] = None
    min_inning: Optional[int] = None
    max_inning: Optional[int] = None
    outs: Optional[list[int]] = None
    runners_on: Optional[str] = None

    # ── Score ──────────────────────────────────────────────────────────
    score_diff_min: Optional[int] = None
    score_diff_max: Optional[int] = None

    # ── Park / Count ──────────────────────────────────────────────────
    park_ids: Optional[list[int]] = None
    balls: Optional[list[int]] = None
    strikes: Optional[list[int]] = None

    # ── Grouping & Pagination ─────────────────────────────────────────
    group_by: Optional[list[str]] = Field(
        default=["pitcher"],
        description="Group by: 'pitcher', 'batter', 'pitcher_team', 'season', 'month', etc.",
    )
    min_pa: Optional[int] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)
    sort_by: Optional[str] = None
    sort_dir: Optional[str] = "desc"


class StealStatsRequest(BaseModel):
    """Filter parameters for stolen-base stats."""

    runner_ids: Optional[list[int]] = None
    runner_team_ids: Optional[list[int]] = None
    pitcher_ids: Optional[list[int]] = None
    catcher_ids: Optional[list[int]] = None
    seasons: Optional[list[int]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    attempted_base: Optional[str] = None  # "2B", "3B", "HP"
    is_successful: Optional[bool] = None
    group_by: Optional[list[str]] = Field(default=["runner"])
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class BattingStatLine(BaseModel):
    """Computed batting statistics for a group."""

    # Raw counts
    pa: int = 0
    ab: int = 0
    h: int = 0
    singles: int = 0
    doubles: int = 0
    triples: int = 0
    hr: int = 0
    rbi: int = 0
    bb: int = 0
    ibb: int = 0
    hbp: int = 0
    so: int = 0
    sf: int = 0
    sh: int = 0

    # Rates (computed)
    avg: Optional[float] = None
    obp: Optional[float] = None
    slg: Optional[float] = None
    ops: Optional[float] = None
    iso: Optional[float] = None
    babip: Optional[float] = None
    woba: Optional[float] = None
    k_pct: Optional[float] = None
    bb_pct: Optional[float] = None
    hr_per_pa: Optional[float] = None

    # Statcast
    avg_exit_velocity: Optional[float] = None
    avg_launch_angle: Optional[float] = None
    hard_hit_pct: Optional[float] = None
    barrel_pct: Optional[float] = None
    batted_balls: int = 0


class PitchingStatLine(BaseModel):
    """Computed pitching statistics for a group."""

    # Raw counts (from batter-faced perspective)
    pa: int = 0
    ab: int = 0
    h: int = 0
    hr: int = 0
    bb: int = 0
    ibb: int = 0
    hbp: int = 0
    so: int = 0
    sf: int = 0
    rbi: int = 0
    outs_recorded: int = 0

    # Computed
    ip: Optional[float] = None  # innings pitched (display format: 6.1 = 6 and 1/3)
    ip_decimal: Optional[float] = None  # true decimal (6.333...)
    whip: Optional[float] = None
    k_per_9: Optional[float] = None
    bb_per_9: Optional[float] = None
    hr_per_9: Optional[float] = None
    k_pct: Optional[float] = None
    bb_pct: Optional[float] = None
    fip: Optional[float] = None
    avg_against: Optional[float] = None
    obp_against: Optional[float] = None
    slg_against: Optional[float] = None
    babip_against: Optional[float] = None

    # Statcast
    avg_exit_velocity: Optional[float] = None
    avg_launch_angle: Optional[float] = None
    hard_hit_pct: Optional[float] = None


class StealStatLine(BaseModel):
    """Stolen base statistics for a group."""

    attempts: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0
    steal_pct: Optional[float] = None


class BattingStatsResult(BaseModel):
    """A single row of batting stats results with its group keys."""

    group: dict[str, Any]
    stats: BattingStatLine


class PitchingStatsResult(BaseModel):
    """A single row of pitching stats results with its group keys."""

    group: dict[str, Any]
    stats: PitchingStatLine


class StealStatsResult(BaseModel):
    group: dict[str, Any]
    stats: StealStatLine


class BattingStatsResponse(BaseModel):
    filters_applied: dict[str, Any]
    results: list[BattingStatsResult]
    total_results: int


class PitchingStatsResponse(BaseModel):
    filters_applied: dict[str, Any]
    results: list[PitchingStatsResult]
    total_results: int


class StealStatsResponse(BaseModel):
    filters_applied: dict[str, Any]
    results: list[StealStatsResult]
    total_results: int
