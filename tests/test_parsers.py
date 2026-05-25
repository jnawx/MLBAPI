"""
Unit tests for the game feed parser.

Tests the parser logic with synthetic MLB API-shaped data to verify
at-bat extraction, pitch parsing, runner tracking, steal detection,
and count/hit-data extraction.
"""

import pytest
from datetime import date

from ingestion.parsers import (
    ParsedPitch,
    _GameState,
    _base_str_to_num,
    _extract_steals,
    _get_count_before_final_pitch,
    _get_hit_data,
    _parse_pitches,
    parse_game_feed,
)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestBaseStrToNum:
    def test_first_base(self):
        assert _base_str_to_num("1B") == 1

    def test_second_base(self):
        assert _base_str_to_num("2B") == 2

    def test_third_base(self):
        assert _base_str_to_num("3B") == 3

    def test_invalid_base(self):
        assert _base_str_to_num("HP") is None

    def test_empty_string(self):
        assert _base_str_to_num("") is None


# ---------------------------------------------------------------------------
# Game state tracker
# ---------------------------------------------------------------------------


class TestGameState:
    def test_initial_state_is_empty(self):
        state = _GameState()
        assert state.get_runner(1) is None
        assert state.get_runner(2) is None
        assert state.get_runner(3) is None
        assert state.home_score == 0
        assert state.away_score == 0

    def test_runner_advances_to_first(self):
        state = _GameState()
        play = {
            "runners": [
                {
                    "movement": {"originBase": None, "end": "1B", "isOut": False},
                    "details": {"runner": {"id": 12345}},
                }
            ],
            "result": {"homeScore": 0, "awayScore": 0},
        }
        state.update_from_play(play)
        assert state.get_runner(1) == 12345
        assert state.get_runner(2) is None
        assert state.get_runner(3) is None

    def test_runner_advances_first_to_second(self):
        state = _GameState()
        state.runners[1] = 11111
        play = {
            "runners": [
                {
                    "movement": {"originBase": "1B", "end": "2B", "isOut": False},
                    "details": {"runner": {"id": 11111}},
                },
                {
                    "movement": {"originBase": None, "end": "1B", "isOut": False},
                    "details": {"runner": {"id": 22222}},
                },
            ],
            "result": {"homeScore": 0, "awayScore": 0},
        }
        state.update_from_play(play)
        assert state.get_runner(1) == 22222
        assert state.get_runner(2) == 11111

    def test_runner_scores(self):
        state = _GameState()
        state.runners[3] = 99999
        play = {
            "runners": [
                {
                    "movement": {"originBase": "3B", "end": "score", "isOut": False},
                    "details": {"runner": {"id": 99999}},
                }
            ],
            "result": {"homeScore": 1, "awayScore": 0},
        }
        state.update_from_play(play)
        assert state.get_runner(3) is None
        assert state.home_score == 1

    def test_runner_out(self):
        state = _GameState()
        state.runners[1] = 55555
        play = {
            "runners": [
                {
                    "movement": {"originBase": "1B", "end": None, "isOut": True},
                    "details": {"runner": {"id": 55555}},
                }
            ],
            "result": {"homeScore": 0, "awayScore": 0},
        }
        state.update_from_play(play)
        assert state.get_runner(1) is None

    def test_reset_for_half_inning(self):
        state = _GameState()
        state.runners = {1: 111, 2: 222, 3: 333}
        state.reset_for_half_inning()
        assert state.get_runner(1) is None
        assert state.get_runner(2) is None
        assert state.get_runner(3) is None

    def test_runner_stays_on_base_when_not_involved(self):
        """A runner not mentioned in the play should remain on their base."""
        state = _GameState()
        state.runners[2] = 77777
        play = {
            "runners": [
                {
                    "movement": {"originBase": None, "end": "1B", "isOut": False},
                    "details": {"runner": {"id": 88888}},
                }
            ],
            "result": {"homeScore": 0, "awayScore": 0},
        }
        state.update_from_play(play)
        assert state.get_runner(1) == 88888
        assert state.get_runner(2) == 77777

    def test_score_updates(self):
        state = _GameState()
        play = {
            "runners": [
                {
                    "movement": {"originBase": None, "end": "score", "isOut": False},
                    "details": {"runner": {"id": 12345}},
                }
            ],
            "result": {"homeScore": 3, "awayScore": 5},
        }
        state.update_from_play(play)
        assert state.home_score == 3
        assert state.away_score == 5


# ---------------------------------------------------------------------------
# Pitch parsing
# ---------------------------------------------------------------------------


class TestParsePitches:
    def test_basic_pitch_sequence(self):
        events = [
            {
                "isPitch": True,
                "details": {
                    "call": {"code": "B", "description": "Ball"},
                    "type": {"code": "FF", "description": "Four-Seam Fastball"},
                },
            },
            {
                "isPitch": True,
                "details": {
                    "call": {"code": "S", "description": "Swinging Strike"},
                    "type": {"code": "SL", "description": "Slider"},
                },
            },
            {
                "isPitch": True,
                "details": {
                    "call": {"code": "X", "description": "In play, out(s)"},
                    "type": {"code": "CH", "description": "Changeup"},
                    "isInPlay": True,
                },
            },
        ]
        pitches = _parse_pitches(events)
        assert len(pitches) == 3
        assert pitches[0].pitch_number == 1
        assert pitches[0].pitch_type == "FF"
        assert pitches[0].pitch_result == "B"
        assert pitches[1].pitch_number == 2
        assert pitches[1].pitch_type == "SL"
        assert pitches[2].pitch_number == 3
        assert pitches[2].pitch_type == "CH"

    def test_non_pitch_events_are_skipped(self):
        events = [
            {"isPitch": False, "details": {}},  # pickoff attempt
            {
                "isPitch": True,
                "details": {
                    "call": {"code": "C", "description": "Called Strike"},
                    "type": {"code": "FF", "description": "Four-Seam Fastball"},
                },
            },
        ]
        pitches = _parse_pitches(events)
        assert len(pitches) == 1
        assert pitches[0].pitch_number == 1

    def test_empty_events(self):
        pitches = _parse_pitches([])
        assert pitches == []


class TestGetCountBeforeFinalPitch:
    def test_multi_pitch_at_bat(self):
        events = [
            {"isPitch": True, "count": {"balls": 0, "strikes": 0}},
            {"isPitch": True, "count": {"balls": 1, "strikes": 0}},
            {"isPitch": True, "count": {"balls": 1, "strikes": 1}},
        ]
        balls, strikes = _get_count_before_final_pitch(events)
        assert balls == 1
        assert strikes == 0

    def test_single_pitch_at_bat(self):
        """First pitch result — count before was 0-0."""
        events = [{"isPitch": True, "count": {"balls": 0, "strikes": 0}}]
        balls, strikes = _get_count_before_final_pitch(events)
        assert balls == 0
        assert strikes == 0

    def test_no_pitches(self):
        balls, strikes = _get_count_before_final_pitch([])
        assert balls == 0
        assert strikes == 0

    def test_non_pitch_events_excluded(self):
        events = [
            {"isPitch": True, "count": {"balls": 0, "strikes": 0}},
            {"isPitch": False, "count": {"balls": 0, "strikes": 0}},  # pickoff
            {"isPitch": True, "count": {"balls": 0, "strikes": 1}},
            {"isPitch": True, "count": {"balls": 1, "strikes": 1}},
        ]
        balls, strikes = _get_count_before_final_pitch(events)
        assert balls == 0
        assert strikes == 1


class TestGetHitData:
    def test_extracts_hit_data(self):
        events = [
            {"isPitch": True, "details": {"call": {"code": "B"}}},
            {
                "isPitch": True,
                "details": {"call": {"code": "X"}, "isInPlay": True},
                "hitData": {
                    "launchSpeed": 105.3,
                    "launchAngle": 28.0,
                    "totalDistance": 410,
                    "trajectory": "fly_ball",
                },
            },
        ]
        hd = _get_hit_data(events)
        assert hd["exit_velocity"] == 105.3
        assert hd["launch_angle"] == 28.0
        assert hd["distance"] == 410
        assert hd["trajectory"] == "fly_ball"

    def test_no_in_play_event(self):
        events = [
            {"isPitch": True, "details": {"call": {"code": "S"}}},
            {"isPitch": True, "details": {"call": {"code": "S"}}},
            {"isPitch": True, "details": {"call": {"code": "S"}}},  # K
        ]
        hd = _get_hit_data(events)
        assert hd == {}

    def test_empty_events(self):
        assert _get_hit_data([]) == {}


# ---------------------------------------------------------------------------
# Steal detection
# ---------------------------------------------------------------------------


class TestExtractSteals:
    def test_successful_steal(self):
        play = {
            "runners": [
                {
                    "movement": {"originBase": "1B", "end": "2B", "isOut": False},
                    "details": {
                        "eventType": "stolen_base_2b",
                        "runner": {"id": 12345},
                        "description": "Steals 2nd",
                    },
                }
            ]
        }
        steals = _extract_steals(
            play, game_mlb_id=100, game_date=date(2024, 7, 1),
            season=2024, inning=3, half_inning="top",
            outs_before=1, batting_team_id=147, pitcher_id=99999,
        )
        assert len(steals) == 1
        assert steals[0].runner_mlb_id == 12345
        assert steals[0].attempted_base == "2B"
        assert steals[0].is_successful is True

    def test_caught_stealing(self):
        play = {
            "runners": [
                {
                    "movement": {"originBase": "1B", "end": None, "isOut": True},
                    "details": {
                        "eventType": "caught_stealing_2b",
                        "runner": {"id": 54321},
                    },
                }
            ]
        }
        steals = _extract_steals(
            play, game_mlb_id=100, game_date=date(2024, 7, 1),
            season=2024, inning=5, half_inning="bottom",
            outs_before=0, batting_team_id=110, pitcher_id=88888,
        )
        assert len(steals) == 1
        assert steals[0].is_successful is False
        assert steals[0].attempted_base == "2B"

    def test_no_steal_events(self):
        play = {
            "runners": [
                {
                    "movement": {"originBase": None, "end": "1B", "isOut": False},
                    "details": {"eventType": "single", "runner": {"id": 11111}},
                }
            ]
        }
        steals = _extract_steals(
            play, game_mlb_id=100, game_date=date(2024, 7, 1),
            season=2024, inning=1, half_inning="top",
            outs_before=0, batting_team_id=147, pitcher_id=99999,
        )
        assert steals == []

    def test_steal_of_third(self):
        play = {
            "runners": [
                {
                    "movement": {"originBase": "2B", "end": "3B", "isOut": False},
                    "details": {
                        "eventType": "stolen_base_3b",
                        "runner": {"id": 67890},
                    },
                }
            ]
        }
        steals = _extract_steals(
            play, game_mlb_id=100, game_date=date(2024, 7, 1),
            season=2024, inning=7, half_inning="top",
            outs_before=1, batting_team_id=147, pitcher_id=99999,
        )
        assert len(steals) == 1
        assert steals[0].attempted_base == "3B"

    def test_steal_of_home(self):
        play = {
            "runners": [
                {
                    "movement": {"originBase": "3B", "end": "score", "isOut": False},
                    "details": {
                        "eventType": "stolen_base_home",
                        "runner": {"id": 11111},
                    },
                }
            ]
        }
        steals = _extract_steals(
            play, game_mlb_id=100, game_date=date(2024, 7, 1),
            season=2024, inning=9, half_inning="bottom",
            outs_before=0, batting_team_id=110, pitcher_id=88888,
        )
        assert len(steals) == 1
        assert steals[0].attempted_base == "HP"
        assert steals[0].is_successful is True


# ---------------------------------------------------------------------------
# Full game feed parser
# ---------------------------------------------------------------------------


class TestParseGameFeed:
    """Test the full parse_game_feed() with a minimal synthetic feed."""

    @pytest.fixture
    def minimal_feed(self):
        """A synthetic game feed with 1 play: a single to center field."""
        return {
            "gameData": {
                "game": {"pk": 717465, "season": "2024", "type": "R"},
                "datetime": {
                    "dateTime": "2024-07-01T23:10:00Z",
                    "officialDate": "2024-07-01",
                    "dayNight": "night",
                },
                "teams": {
                    "home": {"id": 147},
                    "away": {"id": 110},
                },
                "venue": {"id": 3313},
                "status": {"detailedState": "Final"},
                "players": {
                    "ID660271": {
                        "id": 660271,
                        "fullName": "Shohei Ohtani",
                        "firstName": "Shohei",
                        "lastName": "Ohtani",
                        "batSide": {"code": "L"},
                        "pitchHand": {"code": "R"},
                        "primaryPosition": {"abbreviation": "DH"},
                    },
                    "ID543037": {
                        "id": 543037,
                        "fullName": "Max Scherzer",
                        "firstName": "Max",
                        "lastName": "Scherzer",
                        "batSide": {"code": "R"},
                        "pitchHand": {"code": "R"},
                        "primaryPosition": {"abbreviation": "SP"},
                    },
                },
            },
            "liveData": {
                "linescore": {
                    "currentInning": 9,
                    "teams": {
                        "home": {"runs": 5},
                        "away": {"runs": 3},
                    },
                },
                "plays": {
                    "allPlays": [
                        {
                            "about": {
                                "atBatIndex": 0,
                                "inning": 1,
                                "halfInning": "top",
                                "isTopInning": True,
                                "outs": 0,
                            },
                            "matchup": {
                                "batter": {"id": 660271},
                                "pitcher": {"id": 543037},
                                "batSide": {"code": "L"},
                                "pitchHand": {"code": "R"},
                                "battingOrder": "100",
                            },
                            "result": {
                                "event": "Single",
                                "eventType": "single",
                                "rbi": 0,
                                "description": "Ohtani singles to center",
                                "homeScore": 0,
                                "awayScore": 0,
                            },
                            "playEvents": [
                                {
                                    "isPitch": True,
                                    "details": {
                                        "call": {"code": "B", "description": "Ball"},
                                        "type": {"code": "FF", "description": "Four-Seam Fastball"},
                                    },
                                    "count": {"balls": 1, "strikes": 0},
                                },
                                {
                                    "isPitch": True,
                                    "details": {
                                        "call": {"code": "X", "description": "In play, no out"},
                                        "type": {"code": "SL", "description": "Slider"},
                                        "isInPlay": True,
                                    },
                                    "count": {"balls": 1, "strikes": 0},
                                    "hitData": {
                                        "launchSpeed": 98.5,
                                        "launchAngle": 15.2,
                                        "totalDistance": 280,
                                        "trajectory": "line_drive",
                                    },
                                },
                            ],
                            "runners": [
                                {
                                    "movement": {
                                        "originBase": None,
                                        "end": "1B",
                                        "isOut": False,
                                    },
                                    "details": {
                                        "eventType": "single",
                                        "runner": {"id": 660271},
                                    },
                                }
                            ],
                        }
                    ],
                },
            },
        }

    def test_game_metadata(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        assert result.game_mlb_id == 717465
        assert result.season == 2024
        assert result.game_type == "R"
        assert result.game_date == date(2024, 7, 1)
        assert result.day_night == "night"
        assert result.home_team_mlb_id == 147
        assert result.away_team_mlb_id == 110
        assert result.home_score == 5
        assert result.away_score == 3
        assert result.park_mlb_id == 3313
        assert result.status == "Final"

    def test_at_bat_count(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        assert len(result.at_bats) == 1

    def test_at_bat_participants(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        ab = result.at_bats[0]
        assert ab.batter_mlb_id == 660271
        assert ab.pitcher_mlb_id == 543037
        assert ab.batter_team_mlb_id == 110  # away team batting in top
        assert ab.pitcher_team_mlb_id == 147  # home team pitching
        assert ab.batter_is_home is False  # top of inning = away batter

    def test_at_bat_handedness(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        ab = result.at_bats[0]
        assert ab.bat_side == "L"
        assert ab.pitch_hand == "R"

    def test_at_bat_situation(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        ab = result.at_bats[0]
        assert ab.inning == 1
        assert ab.half_inning == "top"
        assert ab.batting_order_position == 1
        assert ab.outs_before == 0
        assert ab.runner_on_1b_mlb_id is None  # bases empty at start
        assert ab.runner_on_2b_mlb_id is None
        assert ab.runner_on_3b_mlb_id is None
        assert ab.batting_team_score == 0
        assert ab.fielding_team_score == 0

    def test_at_bat_count(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        ab = result.at_bats[0]
        # Count before final pitch: 1 ball, 0 strikes (from first pitch)
        assert ab.balls == 1
        assert ab.strikes == 0

    def test_at_bat_result(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        ab = result.at_bats[0]
        assert ab.event == "Single"
        assert ab.event_type == "single"
        assert ab.rbi == 0

    def test_at_bat_statcast(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        ab = result.at_bats[0]
        assert ab.hit_exit_velocity == 98.5
        assert ab.hit_launch_angle == 15.2
        assert ab.hit_distance == 280
        assert ab.hit_trajectory == "line_drive"

    def test_pitches_parsed(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        pitches = result.pitches.get(0, [])
        assert len(pitches) == 2
        assert pitches[0].pitch_type == "FF"
        assert pitches[0].pitch_result == "B"
        assert pitches[1].pitch_type == "SL"
        assert pitches[1].pitch_result == "X"

    def test_player_refs_extracted(self, minimal_feed):
        result = parse_game_feed(minimal_feed)
        assert 660271 in result.player_refs
        assert result.player_refs[660271].full_name == "Shohei Ohtani"
        assert result.player_refs[660271].bat_side == "L"
        assert 543037 in result.player_refs
        assert result.player_refs[543037].full_name == "Max Scherzer"

    def test_empty_game_feed(self):
        """Parser should handle a feed with no plays gracefully."""
        feed = {
            "gameData": {
                "game": {"pk": 1, "season": "2024", "type": "R"},
                "datetime": {"officialDate": "2024-07-01"},
                "teams": {"home": {"id": 1}, "away": {"id": 2}},
                "venue": {"id": 1},
                "status": {"detailedState": "Postponed"},
                "players": {},
            },
            "liveData": {
                "linescore": {"teams": {"home": {}, "away": {}}},
                "plays": {"allPlays": []},
            },
        }
        result = parse_game_feed(feed)
        assert result.at_bats == []
        assert result.steal_attempts == []
