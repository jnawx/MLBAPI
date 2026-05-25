"""
Parsers for MLB Stats API responses.

Converts raw MLB API JSON into dictionaries ready for database insertion.
The main entry point is `parse_game_feed()` which processes a full game's
live feed and returns at-bats, pitches, steal attempts, and player/park
references encountered.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class ParsedAtBat:
    """An at-bat record ready for database insertion."""

    game_mlb_id: int
    game_date: date
    season: int
    game_type: str
    park_mlb_id: Optional[int]
    day_night: Optional[str]
    at_bat_number: int
    batter_mlb_id: int
    batter_team_mlb_id: int
    pitcher_mlb_id: int
    pitcher_team_mlb_id: int
    batter_is_home: bool
    bat_side: str
    pitch_hand: str
    inning: int
    half_inning: str
    batting_order_position: int
    outs_before: int
    runner_on_1b_mlb_id: Optional[int]
    runner_on_2b_mlb_id: Optional[int]
    runner_on_3b_mlb_id: Optional[int]
    batting_team_score: int
    fielding_team_score: int
    balls: int
    strikes: int
    event: str
    event_type: str
    rbi: int
    outs_on_play: int
    hit_exit_velocity: Optional[float]
    hit_launch_angle: Optional[float]
    hit_distance: Optional[float]
    hit_trajectory: Optional[str]
    description: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ParsedPitch:
    """A single pitch within an at-bat."""

    pitch_number: int
    pitch_type: Optional[str]
    pitch_type_description: Optional[str]
    pitch_result: str
    pitch_result_description: Optional[str]


@dataclass
class ParsedStealAttempt:
    """A stolen-base attempt."""

    game_mlb_id: int
    game_date: date
    season: int
    inning: int
    half_inning: str
    runner_mlb_id: int
    runner_team_mlb_id: int
    pitcher_mlb_id: int
    catcher_mlb_id: Optional[int]
    attempted_base: str
    is_successful: bool
    outs_before: int
    description: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ParsedPlayerRef:
    """Minimal player reference extracted from game data."""

    mlb_id: int
    full_name: str
    first_name: str = ""
    last_name: str = ""
    bat_side: Optional[str] = None
    pitch_hand: Optional[str] = None
    primary_position: Optional[str] = None


@dataclass
class ParsedGame:
    """All parsed data from a single game feed."""

    game_mlb_id: int
    game_date: date
    season: int
    game_type: str
    status: str
    game_datetime: Optional[datetime]
    day_night: Optional[str]
    home_team_mlb_id: int
    away_team_mlb_id: int
    home_score: int
    away_score: int
    park_mlb_id: Optional[int]
    double_header: Optional[str]
    game_number: int
    innings_played: int
    home_plate_umpire_mlb_id: Optional[int] = None
    at_bats: list[ParsedAtBat] = field(default_factory=list)
    pitches: dict[int, list[ParsedPitch]] = field(default_factory=dict)  # keyed by at_bat_number
    steal_attempts: list[ParsedStealAttempt] = field(default_factory=list)
    player_refs: dict[int, ParsedPlayerRef] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Game-state tracker
# ---------------------------------------------------------------------------


class _GameState:
    """Tracks runners on base and score as we iterate through plays."""

    def __init__(self) -> None:
        # base -> player MLB ID (None = empty)
        self.runners: dict[int, Optional[int]] = {1: None, 2: None, 3: None}
        self.home_score: int = 0
        self.away_score: int = 0

    def get_runner(self, base: int) -> Optional[int]:
        return self.runners.get(base)

    def update_from_play(self, play: dict[str, Any]) -> None:
        """Update base runners and score after processing a play."""
        runner_events = play.get("runners", [])
        if not runner_events:
            return

        # Track which bases had runners who moved away
        moved_from_bases: set[int] = set()
        new_occupants: dict[int, Optional[int]] = {1: None, 2: None, 3: None}

        for runner in runner_events:
            movement = runner.get("movement", {})
            origin_base_str = movement.get("originBase")  # "1B", "2B", "3B" or None (batter)
            end_base_str = movement.get("end")  # "1B", "2B", "3B", "score", or None (out)
            is_out = movement.get("isOut", False)
            runner_id = runner.get("details", {}).get("runner", {}).get("id")

            if origin_base_str:
                origin_num = _base_str_to_num(origin_base_str)
                if origin_num:
                    moved_from_bases.add(origin_num)

            if end_base_str and not is_out and runner_id:
                end_num = _base_str_to_num(end_base_str)
                if end_num:
                    new_occupants[end_num] = runner_id

        # Runners who didn't move stay on their base
        for base_num in [1, 2, 3]:
            if self.runners[base_num] and base_num not in moved_from_bases:
                if new_occupants[base_num] is None:
                    new_occupants[base_num] = self.runners[base_num]

        self.runners = new_occupants

        # Update score
        result = play.get("result", {})
        self.home_score = result.get("homeScore", self.home_score)
        self.away_score = result.get("awayScore", self.away_score)

    def reset_for_half_inning(self) -> None:
        """Clear the bases at the start of a new half-inning."""
        self.runners = {1: None, 2: None, 3: None}


def _base_str_to_num(base_str: str) -> Optional[int]:
    return {"1B": 1, "2B": 2, "3B": 3}.get(base_str)


# ---------------------------------------------------------------------------
# Pitch parsing
# ---------------------------------------------------------------------------


def _parse_pitches(play_events: list[dict]) -> list[ParsedPitch]:
    """Extract individual pitches from a play's events."""
    pitches: list[ParsedPitch] = []
    pitch_num = 0
    for event in play_events:
        if not event.get("isPitch", False):
            continue
        pitch_num += 1
        details = event.get("details", {})
        call = details.get("call", {})
        ptype = details.get("type", {})

        pitches.append(
            ParsedPitch(
                pitch_number=pitch_num,
                pitch_type=ptype.get("code"),
                pitch_type_description=ptype.get("description"),
                pitch_result=call.get("code", ""),
                pitch_result_description=call.get("description"),
            )
        )
    return pitches


def _get_count_before_final_pitch(play_events: list[dict]) -> tuple[int, int]:
    """Get the (balls, strikes) count before the final pitch of the at-bat."""
    pitch_events = [e for e in play_events if e.get("isPitch", False)]
    if len(pitch_events) <= 1:
        return (0, 0)
    second_to_last = pitch_events[-2]
    count = second_to_last.get("count", {})
    return (count.get("balls", 0), count.get("strikes", 0))


def _get_hit_data(play_events: list[dict]) -> dict[str, Any]:
    """Extract Statcast hit data from the final in-play pitch event."""
    for event in reversed(play_events):
        if event.get("isPitch") and event.get("details", {}).get("isInPlay"):
            hd = event.get("hitData", {})
            if hd:
                return {
                    "exit_velocity": hd.get("launchSpeed"),
                    "launch_angle": hd.get("launchAngle"),
                    "distance": hd.get("totalDistance"),
                    "trajectory": hd.get("trajectory"),
                }
    return {}


# ---------------------------------------------------------------------------
# Steal detection
# ---------------------------------------------------------------------------

_STEAL_EVENTS = frozenset([
    "stolen_base_2b", "stolen_base_3b", "stolen_base_home",
    "caught_stealing_2b", "caught_stealing_3b", "caught_stealing_home",
])

_STEAL_BASE_MAP = {
    "stolen_base_2b": "2B",
    "stolen_base_3b": "3B",
    "stolen_base_home": "HP",
    "caught_stealing_2b": "2B",
    "caught_stealing_3b": "3B",
    "caught_stealing_home": "HP",
}


def _extract_steals(
    play: dict,
    game_mlb_id: int,
    game_date: date,
    season: int,
    inning: int,
    half_inning: str,
    outs_before: int,
    batting_team_id: int,
    pitcher_id: int,
) -> list[ParsedStealAttempt]:
    """Extract steal attempts from a play's runner events."""
    steals = []
    for runner in play.get("runners", []):
        details = runner.get("details", {})
        event_type = details.get("eventType", "")

        if event_type in _STEAL_EVENTS:
            runner_id = details.get("runner", {}).get("id")
            if not runner_id:
                continue

            is_success = event_type.startswith("stolen_base")
            base = _STEAL_BASE_MAP.get(event_type, "2B")

            steals.append(
                ParsedStealAttempt(
                    game_mlb_id=game_mlb_id,
                    game_date=game_date,
                    season=season,
                    inning=inning,
                    half_inning=half_inning,
                    runner_mlb_id=runner_id,
                    runner_team_mlb_id=batting_team_id,
                    pitcher_mlb_id=pitcher_id,
                    catcher_mlb_id=None,  # populated later if available
                    attempted_base=base,
                    is_successful=is_success,
                    outs_before=outs_before,
                    description=details.get("description"),
                )
            )
    return steals


# ---------------------------------------------------------------------------
# Player reference extraction
# ---------------------------------------------------------------------------


def _extract_player_refs(game_data: dict) -> dict[int, ParsedPlayerRef]:
    """Pull player references from the game feed's players dict."""
    refs: dict[int, ParsedPlayerRef] = {}
    players_section = game_data.get("players", {})

    for key, pdata in players_section.items():
        pid = pdata.get("id")
        if not pid:
            continue
        refs[pid] = ParsedPlayerRef(
            mlb_id=pid,
            full_name=pdata.get("fullName", "Unknown"),
            first_name=pdata.get("firstName", ""),
            last_name=pdata.get("lastName", ""),
            bat_side=pdata.get("batSide", {}).get("code"),
            pitch_hand=pdata.get("pitchHand", {}).get("code"),
            primary_position=pdata.get("primaryPosition", {}).get("abbreviation"),
        )
    return refs


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_game_feed(feed: dict[str, Any]) -> ParsedGame:
    """
    Parse a complete MLB live game feed into structured data.

    Parameters
    ----------
    feed : dict
        The JSON response from /api/v1.1/game/{pk}/feed/live

    Returns
    -------
    ParsedGame
        Contains all at-bats, pitches, steal attempts, and player refs.
    """
    game_data = feed.get("gameData", {})
    live_data = feed.get("liveData", {})

    # ── Game metadata ─────────────────────────────────────────────────
    game_info = game_data.get("game", {})
    game_pk = game_info.get("pk")
    season = int(game_info.get("season", 0))
    game_type = game_info.get("type", "R")

    dt_info = game_data.get("datetime", {})
    game_datetime_str = dt_info.get("dateTime")
    game_datetime = None
    game_date_val = None
    if game_datetime_str:
        try:
            game_datetime = datetime.fromisoformat(game_datetime_str.replace("Z", "+00:00"))
            game_date_val = game_datetime.date()
        except (ValueError, TypeError):
            pass
    if game_date_val is None:
        official_date = dt_info.get("officialDate", "")
        if official_date:
            game_date_val = date.fromisoformat(official_date)
        else:
            game_date_val = date.today()

    day_night = dt_info.get("dayNight")

    # Teams
    teams_data = game_data.get("teams", {})
    home_team_id = teams_data.get("home", {}).get("id", 0)
    away_team_id = teams_data.get("away", {}).get("id", 0)

    # Venue
    venue_id = game_data.get("venue", {}).get("id")

    # Status
    status_data = game_data.get("status", {})
    status = status_data.get("detailedState", "Unknown")

    # Score
    line_score = live_data.get("linescore", {})
    home_score = line_score.get("teams", {}).get("home", {}).get("runs", 0)
    away_score = line_score.get("teams", {}).get("away", {}).get("runs", 0)
    innings_played = line_score.get("currentInning", 9)

    # Double-header info
    double_header = game_info.get("doubleHeader", "N")
    game_number = game_info.get("gameNumber", 1)

    # Player references
    player_refs = _extract_player_refs(game_data)

    # Home plate umpire
    home_plate_umpire_id: Optional[int] = None
    officials = live_data.get("boxscore", {}).get("officials", [])
    for official in officials:
        if official.get("officialType") == "Home Plate":
            home_plate_umpire_id = official.get("official", {}).get("id")
            break

    # ── Parse plays ───────────────────────────────────────────────────
    all_plays = live_data.get("plays", {}).get("allPlays", [])
    state = _GameState()

    parsed_at_bats: list[ParsedAtBat] = []
    parsed_pitches: dict[int, list[ParsedPitch]] = {}
    parsed_steals: list[ParsedStealAttempt] = []

    last_half_inning: Optional[str] = None

    # Track batting order per game-side: {is_home: {batter_id: pos}}
    _lineup: dict[bool, dict[int, int]] = {True: {}, False: {}}
    _lineup_counter: dict[bool, int] = {True: 0, False: 0}

    for play in all_plays:
        about = play.get("about", {})
        inning = about.get("inning", 1)
        half_inning = about.get("halfInning", "top")  # "top" or "bottom"
        is_top = about.get("isTopInning", True)
        at_bat_index = about.get("atBatIndex", 0)

        # Reset runners when half-inning changes
        current_half = f"{inning}_{half_inning}"
        if last_half_inning is not None and current_half != last_half_inning:
            state.reset_for_half_inning()
        last_half_inning = current_half

        # Determine batting / fielding teams
        if is_top:
            batting_team_id = away_team_id
            fielding_team_id = home_team_id
            batting_score = state.away_score
            fielding_score = state.home_score
        else:
            batting_team_id = home_team_id
            fielding_team_id = away_team_id
            batting_score = state.home_score
            fielding_score = state.away_score

        batter_is_home = not is_top

        # Matchup
        matchup = play.get("matchup", {})
        batter_id = matchup.get("batter", {}).get("id")
        pitcher_id = matchup.get("pitcher", {}).get("id")
        bat_side = matchup.get("batSide", {}).get("code", "R")
        pitch_hand = matchup.get("pitchHand", {}).get("code", "R")

        if not batter_id or not pitcher_id:
            state.update_from_play(play)
            continue

        # Batting order: derive from sequence of unique batters per side
        _side = batter_is_home
        if batter_id in _lineup[_side]:
            batting_order_position = _lineup[_side][batter_id]
        elif _lineup_counter[_side] < 9:
            _lineup_counter[_side] += 1
            batting_order_position = _lineup_counter[_side]
            _lineup[_side][batter_id] = batting_order_position
        else:
            # Pinch-hitter after 9 unique batters — assign next rotation slot
            rot_idx = sum(1 for _ in _lineup[_side]) % 9
            batting_order_position = rot_idx + 1
            _lineup[_side][batter_id] = batting_order_position

        # Outs before the play
        outs_before = about.get("outs", play.get("count", {}).get("outs", 0))

        # Runners BEFORE this at-bat (from tracked state)
        runner_1b = state.get_runner(1)
        runner_2b = state.get_runner(2)
        runner_3b = state.get_runner(3)

        # Play events (pitches)
        play_events = play.get("playEvents", [])
        balls, strikes = _get_count_before_final_pitch(play_events)
        pitches = _parse_pitches(play_events)
        hit_data = _get_hit_data(play_events)

        # Result
        result = play.get("result", {})
        event = result.get("event", "Unknown")
        event_type = result.get("eventType", "unknown")
        rbi = result.get("rbi", 0)

        # Count outs on play from runner movements
        outs_on_play = sum(
            1
            for r in play.get("runners", [])
            if r.get("movement", {}).get("isOut", False)
        )

        # ── Extract steal attempts ──
        steals = _extract_steals(
            play=play,
            game_mlb_id=game_pk,
            game_date=game_date_val,
            season=season,
            inning=inning,
            half_inning=half_inning,
            outs_before=outs_before,
            batting_team_id=batting_team_id,
            pitcher_id=pitcher_id,
        )
        parsed_steals.extend(steals)

        # ── Build the at-bat record ──
        ab = ParsedAtBat(
            game_mlb_id=game_pk,
            game_date=game_date_val,
            season=season,
            game_type=game_type,
            park_mlb_id=venue_id,
            day_night=day_night,
            at_bat_number=at_bat_index,
            batter_mlb_id=batter_id,
            batter_team_mlb_id=batting_team_id,
            pitcher_mlb_id=pitcher_id,
            pitcher_team_mlb_id=fielding_team_id,
            batter_is_home=batter_is_home,
            bat_side=bat_side,
            pitch_hand=pitch_hand,
            inning=inning,
            half_inning=half_inning,
            batting_order_position=batting_order_position,
            outs_before=outs_before,
            runner_on_1b_mlb_id=runner_1b,
            runner_on_2b_mlb_id=runner_2b,
            runner_on_3b_mlb_id=runner_3b,
            batting_team_score=batting_score,
            fielding_team_score=fielding_score,
            balls=balls,
            strikes=strikes,
            event=event,
            event_type=event_type,
            rbi=rbi,
            outs_on_play=outs_on_play,
            hit_exit_velocity=hit_data.get("exit_velocity"),
            hit_launch_angle=hit_data.get("launch_angle"),
            hit_distance=hit_data.get("distance"),
            hit_trajectory=hit_data.get("trajectory"),
            description=result.get("description"),
        )
        parsed_at_bats.append(ab)
        parsed_pitches[at_bat_index] = pitches

        # Update game state AFTER recording the at-bat
        state.update_from_play(play)

    # ── Assemble parsed game ──────────────────────────────────────────
    return ParsedGame(
        game_mlb_id=game_pk,
        game_date=game_date_val,
        season=season,
        game_type=game_type,
        status=status,
        game_datetime=game_datetime,
        day_night=day_night,
        home_team_mlb_id=home_team_id,
        away_team_mlb_id=away_team_id,
        home_score=home_score or 0,
        away_score=away_score or 0,
        park_mlb_id=venue_id,
        double_header=double_header,
        game_number=game_number,
        innings_played=innings_played or 9,
        home_plate_umpire_mlb_id=home_plate_umpire_id,
        at_bats=parsed_at_bats,
        pitches=parsed_pitches,
        steal_attempts=parsed_steals,
        player_refs=player_refs,
    )
