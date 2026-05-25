from sqlalchemy import Column, Float, Integer, SmallInteger, String

from app.models.base import Base


class Park(Base):
    """MLB ballpark / venue reference data. IDs match official MLB venue IDs."""

    __tablename__ = "parks"

    mlb_id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(150), nullable=False)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    capacity = Column(Integer, nullable=True)
    surface_type = Column(String(30), nullable=True)  # "grass", "artificial"
    roof_type = Column(String(30), nullable=True)  # "open", "retractable", "dome"
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<Park {self.mlb_id} {self.name}>"
