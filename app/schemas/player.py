from datetime import date
from typing import Optional

from pydantic import BaseModel


class PlayerResponse(BaseModel):
    mlb_id: int
    first_name: str
    last_name: str
    full_name: str
    primary_number: Optional[str] = None
    birth_date: Optional[date] = None
    bat_side: Optional[str] = None
    pitch_hand: Optional[str] = None
    primary_position: Optional[str] = None
    mlb_debut_date: Optional[date] = None
    active: bool

    model_config = {"from_attributes": True}


class PlayerListResponse(BaseModel):
    results: list[PlayerResponse]
    total: int
