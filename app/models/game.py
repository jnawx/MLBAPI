from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, SmallInteger, String

from app.models.base import Base


class Game(Base):
    """One row per MLB game. IDs match official MLB game PKs."""

    __tablename__ = "games"

    mlb_game_id = Column(Integer, primary_key=True, autoincrement=False)
    game_date = Column(Date, nullable=False, index=True)
    game_datetime = Column(DateTime(timezone=True), nullable=True)
    season = Column(SmallInteger, nullable=False, index=True)
    game_type = Column(String(2), nullable=False, index=True)  # R, P, S, A, F, D, L, W
    status = Column(String(30), nullable=False)  # "Final", "In Progress", etc.
    day_night = Column(String(10), nullable=True)  # "day", "night"

    # Teams
    home_team_mlb_id = Column(Integer, ForeignKey("teams.mlb_id"), nullable=False, index=True)
    away_team_mlb_id = Column(Integer, ForeignKey("teams.mlb_id"), nullable=False, index=True)

    # Final score
    home_score = Column(SmallInteger, nullable=True)
    away_score = Column(SmallInteger, nullable=True)

    # Venue
    park_mlb_id = Column(Integer, ForeignKey("parks.mlb_id"), nullable=True, index=True)

    # Game metadata
    double_header = Column(String(1), nullable=True)  # "N", "Y", "S" (split)
    game_number = Column(SmallInteger, nullable=True, default=1)  # 1 or 2 for doubleheaders
    innings_played = Column(SmallInteger, nullable=True)

    # Umpire
    home_plate_umpire_mlb_id = Column(Integer, nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<Game {self.mlb_game_id} {self.game_date}>"
