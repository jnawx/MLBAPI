"""
HTTP client for the MLB Stats API.

Provides typed methods for the endpoints we use during data ingestion.
All calls go through a shared httpx.AsyncClient for connection pooling.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE = settings.mlb_api_base_url


class MLBClient:
    """Async HTTP client for the MLB Stats API."""

    def __init__(self, timeout: float = 30.0):
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        """Make a GET request and return the JSON response."""
        url = f"{BASE}{path}"
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Schedule / Games
    # ------------------------------------------------------------------

    async def get_schedule(
        self,
        start_date: date,
        end_date: date,
        sport_id: int = 1,
        game_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get scheduled games for a date range.

        Returns a flat list of game dicts from the schedule API.
        """
        params = {
            "sportId": sport_id,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "hydrate": "team,venue",
        }
        if game_type:
            params["gameType"] = game_type

        data = await self._get("/api/v1/schedule", params)
        games = []
        for date_entry in data.get("dates", []):
            for game in date_entry.get("games", []):
                games.append(game)
        return games

    async def get_game_feed(self, game_pk: int) -> dict[str, Any]:
        """
        Get the full live feed for a game (play-by-play data).

        This is the primary source for at-bat-level data.
        """
        return await self._get(f"/api/v1.1/game/{game_pk}/feed/live")

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    async def get_teams(self, sport_id: int = 1, season: int | None = None) -> list[dict[str, Any]]:
        """Get all MLB teams."""
        params: dict[str, Any] = {"sportId": sport_id}
        if season:
            params["season"] = season
        data = await self._get("/api/v1/teams", params)
        return data.get("teams", [])

    # ------------------------------------------------------------------
    # Players
    # ------------------------------------------------------------------

    async def get_player(self, player_id: int) -> dict[str, Any]:
        """Get a single player's info."""
        data = await self._get(f"/api/v1/people/{player_id}", {"hydrate": "currentTeam"})
        people = data.get("people", [])
        if not people:
            raise ValueError(f"Player {player_id} not found in MLB API")
        return people[0]

    # ------------------------------------------------------------------
    # Venues / Parks
    # ------------------------------------------------------------------

    async def get_venue(self, venue_id: int) -> dict[str, Any]:
        """Get venue details."""
        data = await self._get(f"/api/v1/venues/{venue_id}")
        venues = data.get("venues", [])
        if not venues:
            raise ValueError(f"Venue {venue_id} not found in MLB API")
        return venues[0]
