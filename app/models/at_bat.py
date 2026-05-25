from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)

from app.models.base import Base


class AtBat(Base):
    """
    One row per plate appearance. This is the core table for all stat queries.

    Every field that might be used as a filter is stored as a flat, indexed column
    (no nested JSON) to support fast aggregation across millions of rows.
    """

    __tablename__ = "at_bats"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Game context (denormalized for query performance) ──────────────
    game_mlb_id = Column(Integer, ForeignKey("games.mlb_game_id"), nullable=False)
    game_date = Column(Date, nullable=False)
    season = Column(SmallInteger, nullable=False)
    game_type = Column(String(2), nullable=False, default="R")  # R, P, S, etc.
    park_mlb_id = Column(Integer, ForeignKey("parks.mlb_id"), nullable=True)
    day_night = Column(String(10), nullable=True)  # "day", "night"

    # ── At-bat ordering ───────────────────────────────────────────────
    at_bat_number = Column(SmallInteger, nullable=False)  # order within game

    # ── Participants ──────────────────────────────────────────────────
    batter_mlb_id = Column(Integer, ForeignKey("players.mlb_id"), nullable=False)
    batter_team_mlb_id = Column(Integer, ForeignKey("teams.mlb_id"), nullable=False)
    pitcher_mlb_id = Column(Integer, ForeignKey("players.mlb_id"), nullable=False)
    pitcher_team_mlb_id = Column(Integer, ForeignKey("teams.mlb_id"), nullable=False)
    batter_is_home = Column(Boolean, nullable=False)

    # ── Handedness (resolved per at-bat — switch hitters use actual side) ─
    bat_side = Column(String(1), nullable=False)  # L or R
    pitch_hand = Column(String(1), nullable=False)  # L or R

    # ── Situation ─────────────────────────────────────────────────────
    inning = Column(SmallInteger, nullable=False)
    half_inning = Column(String(6), nullable=False)  # "top" or "bottom"
    batting_order_position = Column(SmallInteger, nullable=False)  # 1–9
    outs_before = Column(SmallInteger, nullable=False)  # 0, 1, or 2

    # Runners on base (MLB IDs — nullable when base is empty)
    runner_on_1b_mlb_id = Column(Integer, ForeignKey("players.mlb_id"), nullable=True)
    runner_on_2b_mlb_id = Column(Integer, ForeignKey("players.mlb_id"), nullable=True)
    runner_on_3b_mlb_id = Column(Integer, ForeignKey("players.mlb_id"), nullable=True)

    # Score BEFORE the at-bat
    batting_team_score = Column(SmallInteger, nullable=False, default=0)
    fielding_team_score = Column(SmallInteger, nullable=False, default=0)

    # ── Count before the final pitch ──────────────────────────────────
    balls = Column(SmallInteger, nullable=False, default=0)
    strikes = Column(SmallInteger, nullable=False, default=0)

    # ── Result ────────────────────────────────────────────────────────
    event = Column(String(60), nullable=False)  # Display: "Single", "Strikeout Looking"
    event_type = Column(String(40), nullable=False)  # Normalized: "single", "strikeout"
    rbi = Column(SmallInteger, nullable=False, default=0)
    outs_on_play = Column(SmallInteger, nullable=False, default=0)  # for computing IP

    # ── Statcast (batted ball only — NULL for non-batted-ball events) ─
    hit_exit_velocity = Column(Float, nullable=True)
    hit_launch_angle = Column(Float, nullable=True)
    hit_distance = Column(Float, nullable=True)
    hit_trajectory = Column(String(20), nullable=True)  # fly_ball, ground_ball, line_drive, popup

    # ── Description ───────────────────────────────────────────────────
    description = Column(Text, nullable=True)

    # ── Indexes ───────────────────────────────────────────────────────
    __table_args__ = (
        # Single-column indexes for the most common filters
        Index("ix_at_bats_game_mlb_id", "game_mlb_id"),
        Index("ix_at_bats_batter_mlb_id", "batter_mlb_id"),
        Index("ix_at_bats_pitcher_mlb_id", "pitcher_mlb_id"),
        Index("ix_at_bats_game_date", "game_date"),
        Index("ix_at_bats_season", "season"),
        Index("ix_at_bats_batter_team", "batter_team_mlb_id"),
        Index("ix_at_bats_pitcher_team", "pitcher_team_mlb_id"),
        Index("ix_at_bats_park", "park_mlb_id"),
        # Composite indexes for common query patterns
        Index("ix_at_bats_batter_season", "batter_mlb_id", "season"),
        Index("ix_at_bats_batter_date", "batter_mlb_id", "game_date"),
        Index("ix_at_bats_pitcher_season", "pitcher_mlb_id", "season"),
        Index("ix_at_bats_batter_team_season", "batter_team_mlb_id", "season"),
        Index("ix_at_bats_splits", "bat_side", "pitch_hand"),
        Index("ix_at_bats_season_type", "season", "game_type"),
        # Unique constraint to prevent duplicate ingestion
        Index("uq_at_bats_game_atbat", "game_mlb_id", "at_bat_number", unique=True),
    )

    def __repr__(self) -> str:
        return f"<AtBat {self.id} game={self.game_mlb_id} #{self.at_bat_number}>"
