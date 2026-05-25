from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class GameResponse(BaseModel):
    mlb_game_id: int
    game_date: date
    game_datetime: Optional[datetime] = None
    season: int
    game_type: str
    status: str
    day_night: Optional[str] = None
    home_team_mlb_id: int
    away_team_mlb_id: int
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    park_mlb_id: Optional[int] = None
    double_header: Optional[str] = None
    game_number: Optional[int] = None
    innings_played: Optional[int] = None

    model_config = {"from_attributes": True}


class GameListResponse(BaseModel):
    results: list[GameResponse]
    total: int
