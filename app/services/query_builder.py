"""
Dynamic query builder for the at-bat stats engine.

Translates filter parameters into efficient SQLAlchemy queries using
PostgreSQL aggregate functions. All filtering happens in SQL so the
database does the heavy lifting.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Select, and_, case, extract, func, literal_column, or_, select
from sqlalchemy.sql.expression import ColumnElement

from app.models.at_bat import AtBat
from app.models.steal_attempt import StealAttempt
from app.schemas.stats import BattingStatsRequest, PitchingStatsRequest, StealStatsRequest

# ---------------------------------------------------------------------------
# Event-type classification (MLB API event_type values)
# ---------------------------------------------------------------------------

NON_AB_EVENTS = frozenset(
    [
        "walk",
        "intent_walk",
        "hit_by_pitch",
        "sac_fly",
        "sac_bunt",
        "sac_fly_double_play",
        "catcher_interf",
    ]
)

HIT_EVENTS = frozenset(["single", "double", "triple", "home_run"])


# ---------------------------------------------------------------------------
# Helpers: aggregation expressions
# ---------------------------------------------------------------------------


def _sum_where(condition: ColumnElement) -> ColumnElement:
    """SUM(CASE WHEN condition THEN 1 ELSE 0 END)"""
    return func.sum(case((condition, 1), else_=0))


def _batting_aggregates() -> list[ColumnElement]:
    """Standard batting counting-stat aggregates over the at_bats table."""
    return [
        func.count().label("pa"),
        _sum_where(AtBat.event_type.notin_(NON_AB_EVENTS)).label("ab"),
        _sum_where(AtBat.event_type.in_(HIT_EVENTS)).label("h"),
        _sum_where(AtBat.event_type == "single").label("singles"),
        _sum_where(AtBat.event_type == "double").label("doubles"),
        _sum_where(AtBat.event_type == "triple").label("triples"),
        _sum_where(AtBat.event_type == "home_run").label("hr"),
        func.sum(AtBat.rbi).label("rbi"),
        _sum_where(AtBat.event_type.in_(["walk", "intent_walk"])).label("bb"),
        _sum_where(AtBat.event_type == "intent_walk").label("ibb"),
        _sum_where(AtBat.event_type == "hit_by_pitch").label("hbp"),
        _sum_where(AtBat.event_type == "strikeout").label("so"),
        _sum_where(AtBat.event_type == "sac_fly").label("sf"),
        _sum_where(AtBat.event_type.in_(["sac_bunt", "sac_fly_double_play"])).label("sh"),
        # Statcast aggregates
        func.avg(AtBat.hit_exit_velocity).label("avg_exit_velocity"),
        func.avg(AtBat.hit_launch_angle).label("avg_launch_angle"),
        _sum_where(AtBat.hit_exit_velocity >= 95.0).label("hard_hit"),
        _sum_where(
            and_(
                AtBat.hit_exit_velocity >= 98.0,
                AtBat.hit_launch_angle.between(26.0, 30.0),
            )
        ).label("barrels"),
        _sum_where(AtBat.hit_exit_velocity.isnot(None)).label("batted_balls"),
    ]


def _pitching_aggregates() -> list[ColumnElement]:
    """Pitching aggregates — same raw counts but we also need outs recorded."""
    return _batting_aggregates() + [
        func.sum(AtBat.outs_on_play).label("outs_recorded"),
    ]


# ---------------------------------------------------------------------------
# Group-by column mapping
# ---------------------------------------------------------------------------

_GROUP_COLUMN_MAP: dict[str, ColumnElement] = {
    "batter": AtBat.batter_mlb_id,
    "pitcher": AtBat.pitcher_mlb_id,
    "batter_team": AtBat.batter_team_mlb_id,
    "pitcher_team": AtBat.pitcher_team_mlb_id,
    "season": AtBat.season,
    "month": extract("month", AtBat.game_date).label("month"),
    "park": AtBat.park_mlb_id,
    "bat_side": AtBat.bat_side,
    "pitch_hand": AtBat.pitch_hand,
    "batting_order_position": AtBat.batting_order_position,
    "inning": AtBat.inning,
    "home_away": AtBat.batter_is_home,
    "day_night": AtBat.day_night,
}


def _resolve_group_columns(group_by: list[str] | None) -> list[ColumnElement]:
    """Convert group_by string names to SQLAlchemy column expressions."""
    if not group_by:
        return []
    cols = []
    for name in group_by:
        if name == "league":
            # League grouping doesn't apply at the at-bat level without a join;
            # return an empty group (all data aggregated together).
            continue
        col = _GROUP_COLUMN_MAP.get(name)
        if col is not None:
            cols.append(col)
    return cols


# ---------------------------------------------------------------------------
# Shared filter application
# ---------------------------------------------------------------------------


def _apply_common_filters(query: Select, params: Any) -> Select:
    """Apply filters that are shared between batting and pitching queries."""

    # Time filters
    if params.seasons:
        query = query.where(AtBat.season.in_(params.seasons))
    if params.date_from:
        query = query.where(AtBat.game_date >= params.date_from)
    if params.date_to:
        query = query.where(AtBat.game_date <= params.date_to)
    if params.months:
        query = query.where(extract("month", AtBat.game_date).in_(params.months))
    if params.game_type:
        query = query.where(AtBat.game_type == params.game_type)

    # Situation filters
    if params.innings:
        query = query.where(AtBat.inning.in_(params.innings))
    if getattr(params, "min_inning", None) is not None:
        query = query.where(AtBat.inning >= params.min_inning)
    if getattr(params, "max_inning", None) is not None:
        query = query.where(AtBat.inning <= params.max_inning)
    if params.outs is not None:
        query = query.where(AtBat.outs_before.in_(params.outs))

    # Runner situation
    if params.runners_on:
        query = _apply_runner_filter(query, params.runners_on)

    # Score differential
    if getattr(params, "score_diff_min", None) is not None:
        query = query.where(
            (AtBat.batting_team_score - AtBat.fielding_team_score) >= params.score_diff_min
        )
    if getattr(params, "score_diff_max", None) is not None:
        query = query.where(
            (AtBat.batting_team_score - AtBat.fielding_team_score) <= params.score_diff_max
        )

    # Park
    if getattr(params, "park_ids", None):
        query = query.where(AtBat.park_mlb_id.in_(params.park_ids))

    # Count before final pitch
    if getattr(params, "balls", None) is not None:
        query = query.where(AtBat.balls.in_(params.balls))
    if getattr(params, "strikes", None) is not None:
        query = query.where(AtBat.strikes.in_(params.strikes))

    return query


def _apply_runner_filter(query: Select, runners_on: str) -> Select:
    """Translate a runner situation keyword into WHERE clauses."""
    r = runners_on.lower().strip()
    if r == "empty":
        query = query.where(
            and_(
                AtBat.runner_on_1b_mlb_id.is_(None),
                AtBat.runner_on_2b_mlb_id.is_(None),
                AtBat.runner_on_3b_mlb_id.is_(None),
            )
        )
    elif r == "on_base":
        query = query.where(
            or_(
                AtBat.runner_on_1b_mlb_id.isnot(None),
                AtBat.runner_on_2b_mlb_id.isnot(None),
                AtBat.runner_on_3b_mlb_id.isnot(None),
            )
        )
    elif r == "risp":
        query = query.where(
            or_(
                AtBat.runner_on_2b_mlb_id.isnot(None),
                AtBat.runner_on_3b_mlb_id.isnot(None),
            )
        )
    elif r == "loaded":
        query = query.where(
            and_(
                AtBat.runner_on_1b_mlb_id.isnot(None),
                AtBat.runner_on_2b_mlb_id.isnot(None),
                AtBat.runner_on_3b_mlb_id.isnot(None),
            )
        )
    elif r == "1b":
        query = query.where(AtBat.runner_on_1b_mlb_id.isnot(None))
    elif r == "2b":
        query = query.where(AtBat.runner_on_2b_mlb_id.isnot(None))
    elif r == "3b":
        query = query.where(AtBat.runner_on_3b_mlb_id.isnot(None))
    elif r == "1b_2b":
        query = query.where(
            and_(
                AtBat.runner_on_1b_mlb_id.isnot(None),
                AtBat.runner_on_2b_mlb_id.isnot(None),
            )
        )
    elif r == "1b_3b":
        query = query.where(
            and_(
                AtBat.runner_on_1b_mlb_id.isnot(None),
                AtBat.runner_on_3b_mlb_id.isnot(None),
            )
        )
    elif r == "2b_3b":
        query = query.where(
            and_(
                AtBat.runner_on_2b_mlb_id.isnot(None),
                AtBat.runner_on_3b_mlb_id.isnot(None),
            )
        )
    return query


# ---------------------------------------------------------------------------
# Public API: build complete queries
# ---------------------------------------------------------------------------


def build_batting_stats_query(params: BattingStatsRequest) -> Select:
    """Build a fully-filtered, grouped batting stats query."""
    group_cols = _resolve_group_columns(params.group_by)
    agg_cols = _batting_aggregates()

    query = select(*group_cols, *agg_cols).select_from(AtBat)

    # Batting-specific filters
    if params.batter_ids:
        query = query.where(AtBat.batter_mlb_id.in_(params.batter_ids))
    if params.batter_team_ids:
        query = query.where(AtBat.batter_team_mlb_id.in_(params.batter_team_ids))
    if params.pitcher_ids:
        query = query.where(AtBat.pitcher_mlb_id.in_(params.pitcher_ids))
    if params.pitcher_team_ids:
        query = query.where(AtBat.pitcher_team_mlb_id.in_(params.pitcher_team_ids))
    if params.bat_side:
        query = query.where(AtBat.bat_side == params.bat_side.upper())
    if params.pitch_hand:
        query = query.where(AtBat.pitch_hand == params.pitch_hand.upper())
    if params.home_away:
        is_home = params.home_away.lower() == "home"
        query = query.where(AtBat.batter_is_home == is_home)
    if params.batting_order_positions:
        query = query.where(AtBat.batting_order_position.in_(params.batting_order_positions))

    # Statcast filters
    if params.min_exit_velocity is not None:
        query = query.where(AtBat.hit_exit_velocity >= params.min_exit_velocity)
    if params.max_exit_velocity is not None:
        query = query.where(AtBat.hit_exit_velocity <= params.max_exit_velocity)
    if params.min_launch_angle is not None:
        query = query.where(AtBat.hit_launch_angle >= params.min_launch_angle)
    if params.max_launch_angle is not None:
        query = query.where(AtBat.hit_launch_angle <= params.max_launch_angle)

    # Common filters
    query = _apply_common_filters(query, params)

    # Group by
    if group_cols:
        query = query.group_by(*group_cols)

    # Min PA filter (HAVING)
    if params.min_pa:
        query = query.having(func.count() >= params.min_pa)

    return query


def build_pitching_stats_query(params: PitchingStatsRequest) -> Select:
    """Build a fully-filtered, grouped pitching stats query."""
    group_cols = _resolve_group_columns(params.group_by)
    agg_cols = _pitching_aggregates()

    query = select(*group_cols, *agg_cols).select_from(AtBat)

    # Pitching-specific filters
    if params.pitcher_ids:
        query = query.where(AtBat.pitcher_mlb_id.in_(params.pitcher_ids))
    if params.pitcher_team_ids:
        query = query.where(AtBat.pitcher_team_mlb_id.in_(params.pitcher_team_ids))
    if params.batter_ids:
        query = query.where(AtBat.batter_mlb_id.in_(params.batter_ids))
    if params.batter_team_ids:
        query = query.where(AtBat.batter_team_mlb_id.in_(params.batter_team_ids))
    if params.pitch_hand:
        query = query.where(AtBat.pitch_hand == params.pitch_hand.upper())
    if params.vs_bat_side:
        query = query.where(AtBat.bat_side == params.vs_bat_side.upper())
    if params.home_away:
        # Pitcher is home when batter is away and vice versa
        is_home_pitcher = params.home_away.lower() == "home"
        query = query.where(AtBat.batter_is_home == (not is_home_pitcher))

    # Common filters
    query = _apply_common_filters(query, params)

    # Group by
    if group_cols:
        query = query.group_by(*group_cols)

    # Min PA faced
    if params.min_pa:
        query = query.having(func.count() >= params.min_pa)

    return query


def build_steal_stats_query(params: StealStatsRequest) -> Select:
    """Build a filtered, grouped stolen-base stats query."""
    sa = StealAttempt

    group_map: dict[str, ColumnElement] = {
        "runner": sa.runner_mlb_id,
        "runner_team": sa.runner_team_mlb_id,
        "pitcher": sa.pitcher_mlb_id,
        "catcher": sa.catcher_mlb_id,
        "season": sa.season,
        "attempted_base": sa.attempted_base,
    }

    group_cols = [group_map[g] for g in (params.group_by or []) if g in group_map]

    agg_cols = [
        func.count().label("attempts"),
        _sum_where(sa.is_successful == True).label("stolen_bases"),
        _sum_where(sa.is_successful == False).label("caught_stealing"),
    ]

    query = select(*group_cols, *agg_cols).select_from(sa)

    if params.runner_ids:
        query = query.where(sa.runner_mlb_id.in_(params.runner_ids))
    if params.runner_team_ids:
        query = query.where(sa.runner_team_mlb_id.in_(params.runner_team_ids))
    if params.pitcher_ids:
        query = query.where(sa.pitcher_mlb_id.in_(params.pitcher_ids))
    if params.catcher_ids:
        query = query.where(sa.catcher_mlb_id.in_(params.catcher_ids))
    if params.seasons:
        query = query.where(sa.season.in_(params.seasons))
    if params.date_from:
        query = query.where(sa.game_date >= params.date_from)
    if params.date_to:
        query = query.where(sa.game_date <= params.date_to)
    if params.attempted_base:
        query = query.where(sa.attempted_base == params.attempted_base)
    if params.is_successful is not None:
        query = query.where(sa.is_successful == params.is_successful)

    if group_cols:
        query = query.group_by(*group_cols)

    return query
