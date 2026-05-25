from sqlalchemy import Column, ForeignKey, Index, Integer, SmallInteger, String

from app.models.base import Base


class Pitch(Base):
    """
    One row per pitch within an at-bat.

    Stores the pitch type and result in order, enabling queries like
    'at-bats where a curveball was thrown' or 'at-bats with a first-pitch fastball'.
    """

    __tablename__ = "pitches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    at_bat_id = Column(Integer, ForeignKey("at_bats.id", ondelete="CASCADE"), nullable=False)

    pitch_number = Column(SmallInteger, nullable=False)  # 1-based order within at-bat
    pitch_type = Column(String(10), nullable=True)  # FF, SL, CU, CH, FC, SI, etc.
    pitch_type_description = Column(String(40), nullable=True)  # "Four-Seam Fastball"
    pitch_result = Column(String(2), nullable=False)  # B, C, S, F, X, etc.
    pitch_result_description = Column(String(50), nullable=True)  # "Ball", "Called Strike"

    __table_args__ = (
        Index("ix_pitches_at_bat_id", "at_bat_id"),
        Index("ix_pitches_pitch_type", "pitch_type"),
        Index("uq_pitches_at_bat_num", "at_bat_id", "pitch_number", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Pitch {self.id} ab={self.at_bat_id} #{self.pitch_number} {self.pitch_type}>"
