from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from app.models.base import Base


class Team(Base):
    """MLB team reference data. IDs match official MLB IDs."""

    __tablename__ = "teams"

    mlb_id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(100), nullable=False)  # e.g. "New York Yankees"
    team_name = Column(String(50), nullable=False)  # e.g. "Yankees"
    abbreviation = Column(String(5), nullable=False)  # e.g. "NYY"
    league_name = Column(String(50), nullable=True)  # "American League" / "National League"
    division_name = Column(String(50), nullable=True)  # "American League East"
    venue_mlb_id = Column(Integer, ForeignKey("parks.mlb_id"), nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Team {self.mlb_id} {self.abbreviation}>"
