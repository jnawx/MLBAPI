from typing import Optional

from pydantic import BaseModel


class TeamResponse(BaseModel):
    mlb_id: int
    name: str
    team_name: str
    abbreviation: str
    league_name: Optional[str] = None
    division_name: Optional[str] = None
    venue_mlb_id: Optional[int] = None
    active: bool

    model_config = {"from_attributes": True}


class TeamListResponse(BaseModel):
    results: list[TeamResponse]
    total: int
