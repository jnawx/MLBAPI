from typing import Optional

from pydantic import BaseModel


class ParkResponse(BaseModel):
    mlb_id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    capacity: Optional[int] = None
    surface_type: Optional[str] = None
    roof_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}
