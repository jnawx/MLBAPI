from sqlalchemy import Boolean, Column, Date, ForeignKey, Index, Integer, SmallInteger, String, Text

from app.models.base import Base


class StealAttempt(Base):
    """
    One row per stolen-base attempt (successful or caught stealing).
    Tracked separately from at-bats since steals occur between/during plays.
    """

    __tablename__ = "steal_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Game context
    game_mlb_id = Column(Integer, ForeignKey("games.mlb_game_id"), nullable=False)
    game_date = Column(Date, nullable=False)  # denormalized
    season = Column(SmallInteger, nullable=False)  # denormalized
    inning = Column(SmallInteger, nullable=False)
    half_inning = Column(String(6), nullable=False)  # "top" or "bottom"

    # Participants
    runner_mlb_id = Column(Integer, ForeignKey("players.mlb_id"), nullable=False)
    runner_team_mlb_id = Column(Integer, ForeignKey("teams.mlb_id"), nullable=False)
    pitcher_mlb_id = Column(Integer, ForeignKey("players.mlb_id"), nullable=False)
    catcher_mlb_id = Column(Integer, ForeignKey("players.mlb_id"), nullable=True)

    # Attempt details
    attempted_base = Column(String(4), nullable=False)  # "2B", "3B", "HP"
    is_successful = Column(Boolean, nullable=False)

    # Situation at time of attempt
    outs_before = Column(SmallInteger, nullable=True)

    description = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_steal_game", "game_mlb_id"),
        Index("ix_steal_runner", "runner_mlb_id"),
        Index("ix_steal_runner_season", "runner_mlb_id", "season"),
        Index("ix_steal_pitcher", "pitcher_mlb_id"),
        Index("ix_steal_date", "game_date"),
    )

    def __repr__(self) -> str:
        return f"<StealAttempt {self.id} runner={self.runner_mlb_id} base={self.attempted_base}>"
