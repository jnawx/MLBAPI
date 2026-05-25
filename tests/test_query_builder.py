"""
Unit tests for the query builder — verifies that SQL queries are constructed
correctly based on filter parameters.

These tests compile queries to SQL strings and check that the expected
WHERE clauses, GROUP BY, and HAVING expressions appear.
"""

import pytest
from datetime import date

from sqlalchemy.dialects import postgresql

from app.schemas.stats import BattingStatsRequest, PitchingStatsRequest, StealStatsRequest
from app.services.query_builder import (
    build_batting_stats_query,
    build_pitching_stats_query,
    build_steal_stats_query,
)


def _compile_query(query) -> str:
    """Compile a SQLAlchemy query to a PostgreSQL SQL string for inspection."""
    return str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


# ---------------------------------------------------------------------------
# Batting query builder
# ---------------------------------------------------------------------------


class TestBuildBattingStatsQuery:
    def test_default_query_groups_by_batter(self):
        params = BattingStatsRequest()
        sql = _compile_query(build_batting_stats_query(params))
        assert "batter_mlb_id" in sql
        assert "GROUP BY" in sql

    def test_season_filter(self):
        params = BattingStatsRequest(seasons=[2024])
        sql = _compile_query(build_batting_stats_query(params))
        assert "season" in sql
        assert "2024" in sql

    def test_multi_season_filter(self):
        params = BattingStatsRequest(seasons=[2022, 2023, 2024])
        sql = _compile_query(build_batting_stats_query(params))
        assert "2022" in sql
        assert "2023" in sql
        assert "2024" in sql

    def test_batter_id_filter(self):
        params = BattingStatsRequest(batter_ids=[660271])
        sql = _compile_query(build_batting_stats_query(params))
        assert "660271" in sql

    def test_bat_side_filter(self):
        params = BattingStatsRequest(bat_side="L")
        sql = _compile_query(build_batting_stats_query(params))
        assert "bat_side" in sql

    def test_pitch_hand_filter(self):
        params = BattingStatsRequest(pitch_hand="R")
        sql = _compile_query(build_batting_stats_query(params))
        assert "pitch_hand" in sql

    def test_home_away_filter(self):
        params = BattingStatsRequest(home_away="home")
        sql = _compile_query(build_batting_stats_query(params))
        assert "batter_is_home" in sql

    def test_batting_order_filter(self):
        params = BattingStatsRequest(batting_order_positions=[3, 4])
        sql = _compile_query(build_batting_stats_query(params))
        assert "batting_order_position" in sql

    def test_date_range_filter(self):
        params = BattingStatsRequest(
            date_from=date(2024, 6, 1),
            date_to=date(2024, 8, 31),
        )
        sql = _compile_query(build_batting_stats_query(params))
        assert "game_date" in sql
        assert "2024-06-01" in sql
        assert "2024-08-31" in sql

    def test_runners_on_risp(self):
        params = BattingStatsRequest(runners_on="risp")
        sql = _compile_query(build_batting_stats_query(params))
        assert "runner_on_2b_mlb_id" in sql or "runner_on_3b_mlb_id" in sql

    def test_runners_on_empty(self):
        params = BattingStatsRequest(runners_on="empty")
        sql = _compile_query(build_batting_stats_query(params))
        assert "runner_on_1b_mlb_id IS NULL" in sql

    def test_outs_filter(self):
        params = BattingStatsRequest(outs=[2])
        sql = _compile_query(build_batting_stats_query(params))
        assert "outs_before" in sql

    def test_innings_filter(self):
        params = BattingStatsRequest(innings=[7, 8, 9])
        sql = _compile_query(build_batting_stats_query(params))
        assert "inning" in sql

    def test_min_pa_adds_having(self):
        params = BattingStatsRequest(min_pa=100)
        sql = _compile_query(build_batting_stats_query(params))
        assert "HAVING" in sql

    def test_group_by_season(self):
        params = BattingStatsRequest(group_by=["batter", "season"])
        sql = _compile_query(build_batting_stats_query(params))
        assert "season" in sql
        assert "GROUP BY" in sql

    def test_group_by_multiple(self):
        params = BattingStatsRequest(group_by=["batter", "season", "bat_side"])
        sql = _compile_query(build_batting_stats_query(params))
        assert "bat_side" in sql

    def test_park_filter(self):
        params = BattingStatsRequest(park_ids=[3313])
        sql = _compile_query(build_batting_stats_query(params))
        assert "park_mlb_id" in sql
        assert "3313" in sql

    def test_exit_velocity_filter(self):
        params = BattingStatsRequest(min_exit_velocity=95.0)
        sql = _compile_query(build_batting_stats_query(params))
        assert "hit_exit_velocity" in sql

    def test_game_type_default_is_regular(self):
        params = BattingStatsRequest()
        sql = _compile_query(build_batting_stats_query(params))
        assert "game_type" in sql

    def test_opposing_pitcher_filter(self):
        params = BattingStatsRequest(pitcher_ids=[543037])
        sql = _compile_query(build_batting_stats_query(params))
        assert "pitcher_mlb_id" in sql
        assert "543037" in sql

    def test_opposing_team_filter(self):
        params = BattingStatsRequest(pitcher_team_ids=[147])
        sql = _compile_query(build_batting_stats_query(params))
        assert "pitcher_team_mlb_id" in sql

    def test_batter_team_filter(self):
        params = BattingStatsRequest(batter_team_ids=[147])
        sql = _compile_query(build_batting_stats_query(params))
        assert "batter_team_mlb_id" in sql

    def test_count_filter(self):
        params = BattingStatsRequest(balls=[3], strikes=[2])
        sql = _compile_query(build_batting_stats_query(params))
        assert "balls" in sql
        assert "strikes" in sql

    def test_score_diff_filter(self):
        params = BattingStatsRequest(score_diff_min=-1, score_diff_max=1)
        sql = _compile_query(build_batting_stats_query(params))
        assert "batting_team_score" in sql
        assert "fielding_team_score" in sql

    def test_month_filter(self):
        params = BattingStatsRequest(months=[7, 8])
        sql = _compile_query(build_batting_stats_query(params))
        assert "EXTRACT" in sql.upper() or "extract" in sql

    def test_complex_combined_filters(self):
        """A realistic complex query combining many filters."""
        params = BattingStatsRequest(
            batter_ids=[660271],
            seasons=[2023, 2024],
            bat_side="L",
            pitch_hand="R",
            batting_order_positions=[3, 4],
            runners_on="risp",
            min_pa=50,
            group_by=["batter", "season"],
        )
        sql = _compile_query(build_batting_stats_query(params))
        assert "660271" in sql
        assert "bat_side" in sql
        assert "pitch_hand" in sql
        assert "batting_order_position" in sql
        assert "HAVING" in sql
        assert "GROUP BY" in sql


# ---------------------------------------------------------------------------
# Pitching query builder
# ---------------------------------------------------------------------------


class TestBuildPitchingStatsQuery:
    def test_default_groups_by_pitcher(self):
        params = PitchingStatsRequest()
        sql = _compile_query(build_pitching_stats_query(params))
        assert "pitcher_mlb_id" in sql
        assert "GROUP BY" in sql

    def test_pitcher_id_filter(self):
        params = PitchingStatsRequest(pitcher_ids=[543037])
        sql = _compile_query(build_pitching_stats_query(params))
        assert "543037" in sql

    def test_vs_bat_side_filter(self):
        params = PitchingStatsRequest(vs_bat_side="L")
        sql = _compile_query(build_pitching_stats_query(params))
        assert "bat_side" in sql

    def test_pitcher_home_away(self):
        """When pitcher filters home, batter should be away (batter_is_home = false)."""
        params = PitchingStatsRequest(home_away="home")
        sql = _compile_query(build_pitching_stats_query(params))
        assert "batter_is_home" in sql

    def test_includes_outs_recorded(self):
        """Pitching query should include outs_on_play aggregation."""
        params = PitchingStatsRequest()
        sql = _compile_query(build_pitching_stats_query(params))
        assert "outs_on_play" in sql

    def test_pitcher_team_filter(self):
        params = PitchingStatsRequest(pitcher_team_ids=[147])
        sql = _compile_query(build_pitching_stats_query(params))
        assert "pitcher_team_mlb_id" in sql


# ---------------------------------------------------------------------------
# Steal stats query builder
# ---------------------------------------------------------------------------


class TestBuildStealStatsQuery:
    def test_default_groups_by_runner(self):
        params = StealStatsRequest()
        sql = _compile_query(build_steal_stats_query(params))
        assert "runner_mlb_id" in sql

    def test_runner_filter(self):
        params = StealStatsRequest(runner_ids=[660271])
        sql = _compile_query(build_steal_stats_query(params))
        assert "660271" in sql

    def test_season_filter(self):
        params = StealStatsRequest(seasons=[2024])
        sql = _compile_query(build_steal_stats_query(params))
        assert "2024" in sql

    def test_attempted_base_filter(self):
        params = StealStatsRequest(attempted_base="3B")
        sql = _compile_query(build_steal_stats_query(params))
        assert "attempted_base" in sql

    def test_success_filter(self):
        params = StealStatsRequest(is_successful=True)
        sql = _compile_query(build_steal_stats_query(params))
        assert "is_successful" in sql

    def test_pitcher_filter(self):
        params = StealStatsRequest(pitcher_ids=[543037])
        sql = _compile_query(build_steal_stats_query(params))
        assert "pitcher_mlb_id" in sql

    def test_group_by_season(self):
        params = StealStatsRequest(group_by=["runner", "season"])
        sql = _compile_query(build_steal_stats_query(params))
        assert "season" in sql
        assert "GROUP BY" in sql
