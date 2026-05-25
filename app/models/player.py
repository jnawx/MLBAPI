from sqlalchemy import Boolean, Column, Date, Integer, SmallInteger, String

from app.models.base import Base


class Player(Base):
    """MLB player reference data. IDs match official MLB IDs."""

    __tablename__ = "players"

    mlb_id = Column(Integer, primary_key=True, autoincrement=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    full_name = Column(String(200), nullable=False)
    primary_number = Column(String(10), nullable=True)  # jersey number
    birth_date = Column(Date, nullable=True)
    bat_side = Column(String(1), nullable=True)  # L, R, S (switch)
    pitch_hand = Column(String(1), nullable=True)  # L, R
    primary_position = Column(String(5), nullable=True)  # e.g. "SS", "SP", "CF"
    mlb_debut_date = Column(Date, nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Player {self.mlb_id} {self.full_name}>"
