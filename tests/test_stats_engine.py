"""
Unit tests for the stats engine — verifying all computed statistics.

These tests use hand-calculated values to ensure AVG, OBP, SLG, OPS,
ISO, BABIP, wOBA, K%, BB%, FIP, WHIP, etc. are all correct.
"""

import pytest

from app.services.stats_engine import (
    _safe_div,
    _round_stat,
    compute_batting_stats,
    compute_pitching_stats,
    compute_steal_stats,
)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestSafeDiv:
    def test_normal_division(self):
        assert _safe_div(10, 3) == pytest.approx(3.333333, rel=1e-4)

    def test_divide_by_zero(self):
        assert _safe_div(10, 0) is None

    def test_zero_numerator(self):
        assert _safe_div(0, 5) == 0.0

    def test_negative_values(self):
        assert _safe_div(-6, 3) == -2.0


class TestRoundStat:
    def test_normal_rounding(self):
        assert _round_stat(0.33333, 3) == 0.333

    def test_none_passthrough(self):
        assert _round_stat(None) is None

    def test_default_3_digits(self):
        assert _round_stat(0.12345) == 0.123

    def test_custom_digits(self):
        assert _round_stat(3.14159, 2) == 3.14


# ---------------------------------------------------------------------------
# Batting stats computation
# ---------------------------------------------------------------------------


class TestComputeBattingStats:
    """
    Test case: a hitter with a known stat line.

    500 PA: 130 H (80 1B, 30 2B, 5 3B, 15 HR), 50 BB (5 IBB), 10 HBP,
    120 SO, 5 SF, 0 SH, 80 RBI.
    AB = PA - BB - HBP - SF - SH = 500 - 50 - 10 - 5 - 0 = 435
    """

    @pytest.fixture
    def raw_stats(self):
        return {
            "pa": 500,
            "ab": 435,  # 500 - 50 - 10 - 5
            "h": 130,
            "singles": 80,
            "doubles": 30,
            "triples": 5,
            "hr": 15,
            "rbi": 80,
            "bb": 50,
            "ibb": 5,
            "hbp": 10,
            "so": 120,
            "sf": 5,
            "sh": 0,
            "avg_exit_velocity": 89.5,
            "avg_launch_angle": 12.3,
            "hard_hit": 80,
            "barrels": 20,
            "batted_balls": 300,
        }

    def test_counting_stats(self, raw_stats):
        result = compute_batting_stats(raw_stats)
        assert result.pa == 500
        assert result.ab == 435
        assert result.h == 130
        assert result.singles == 80
        assert result.doubles == 30
        assert result.triples == 5
        assert result.hr == 15
        assert result.rbi == 80
        assert result.bb == 50
        assert result.ibb == 5
        assert result.hbp == 10
        assert result.so == 120
        assert result.sf == 5
        assert result.sh == 0

    def test_batting_average(self, raw_stats):
        # AVG = 130 / 435 = 0.29885...
        result = compute_batting_stats(raw_stats)
        assert result.avg == pytest.approx(0.299, abs=0.001)

    def test_on_base_percentage(self, raw_stats):
        # OBP = (130 + 50 + 10) / (435 + 50 + 10 + 5) = 190 / 500 = 0.380
        result = compute_batting_stats(raw_stats)
        assert result.obp == pytest.approx(0.380, abs=0.001)

    def test_slugging_percentage(self, raw_stats):
        # TB = 130 + 30 + 2*5 + 3*15 = 130 + 30 + 10 + 45 = 215
        # SLG = 215 / 435 = 0.4942...
        result = compute_batting_stats(raw_stats)
        assert result.slg == pytest.approx(0.494, abs=0.001)

    def test_ops(self, raw_stats):
        result = compute_batting_stats(raw_stats)
        assert result.ops == pytest.approx(result.obp + result.slg, abs=0.001)

    def test_iso(self, raw_stats):
        # ISO = SLG - AVG
        result = compute_batting_stats(raw_stats)
        assert result.iso == pytest.approx(result.slg - result.avg, abs=0.001)

    def test_babip(self, raw_stats):
        # BABIP = (H - HR) / (AB - SO - HR + SF) = (130-15) / (435-120-15+5) = 115/305
        result = compute_batting_stats(raw_stats)
        expected = 115 / 305
        assert result.babip == pytest.approx(expected, abs=0.001)

    def test_k_percentage(self, raw_stats):
        # K% = 120 / 500 = 0.240
        result = compute_batting_stats(raw_stats)
        assert result.k_pct == pytest.approx(0.240, abs=0.001)

    def test_bb_percentage(self, raw_stats):
        # BB% = 50 / 500 = 0.100
        result = compute_batting_stats(raw_stats)
        assert result.bb_pct == pytest.approx(0.100, abs=0.001)

    def test_hr_per_pa(self, raw_stats):
        result = compute_batting_stats(raw_stats)
        assert result.hr_per_pa == pytest.approx(15 / 500, abs=0.001)

    def test_woba_computed(self, raw_stats):
        """wOBA should be computed and in a reasonable range."""
        result = compute_batting_stats(raw_stats, season=2024)
        assert result.woba is not None
        assert 0.200 < result.woba < 0.500

    def test_woba_with_specific_season(self, raw_stats):
        """wOBA using 2024 weights should differ from 2021 weights."""
        result_2024 = compute_batting_stats(raw_stats, season=2024)
        result_2021 = compute_batting_stats(raw_stats, season=2021)
        # They should be close but not identical (different weight sets)
        assert result_2024.woba != result_2021.woba

    def test_statcast_averages(self, raw_stats):
        result = compute_batting_stats(raw_stats)
        assert result.avg_exit_velocity == 89.5
        assert result.avg_launch_angle == 12.3

    def test_hard_hit_pct(self, raw_stats):
        # 80 / 300 = 0.2667
        result = compute_batting_stats(raw_stats)
        assert result.hard_hit_pct == pytest.approx(80 / 300, abs=0.001)

    def test_barrel_pct(self, raw_stats):
        # 20 / 300 = 0.0667
        result = compute_batting_stats(raw_stats)
        assert result.barrel_pct == pytest.approx(20 / 300, abs=0.001)

    def test_batted_balls_count(self, raw_stats):
        result = compute_batting_stats(raw_stats)
        assert result.batted_balls == 300


class TestBattingEdgeCases:
    def test_zero_plate_appearances(self):
        raw = {k: 0 for k in [
            "pa", "ab", "h", "singles", "doubles", "triples", "hr", "rbi",
            "bb", "ibb", "hbp", "so", "sf", "sh",
            "avg_exit_velocity", "avg_launch_angle", "hard_hit", "barrels", "batted_balls",
        ]}
        raw["avg_exit_velocity"] = None
        raw["avg_launch_angle"] = None
        result = compute_batting_stats(raw)
        assert result.pa == 0
        assert result.avg is None
        assert result.obp is None
        assert result.slg is None
        assert result.ops is None
        assert result.woba is None
        assert result.k_pct is None
        assert result.bb_pct is None

    def test_hitless_player(self):
        """Player with PAs but no hits — AVG should be 0.000"""
        raw = {
            "pa": 20, "ab": 18, "h": 0, "singles": 0, "doubles": 0,
            "triples": 0, "hr": 0, "rbi": 0, "bb": 2, "ibb": 0,
            "hbp": 0, "so": 10, "sf": 0, "sh": 0,
            "avg_exit_velocity": None, "avg_launch_angle": None,
            "hard_hit": 0, "barrels": 0, "batted_balls": 8,
        }
        result = compute_batting_stats(raw)
        assert result.avg == 0.0
        assert result.slg == 0.0
        assert result.obp == pytest.approx(2 / 20, abs=0.001)
        assert result.hard_hit_pct == 0.0

    def test_perfect_hitter(self):
        """Player who gets a hit every AB."""
        raw = {
            "pa": 10, "ab": 10, "h": 10, "singles": 10, "doubles": 0,
            "triples": 0, "hr": 0, "rbi": 3, "bb": 0, "ibb": 0,
            "hbp": 0, "so": 0, "sf": 0, "sh": 0,
            "avg_exit_velocity": 95.0, "avg_launch_angle": 15.0,
            "hard_hit": 5, "barrels": 1, "batted_balls": 10,
        }
        result = compute_batting_stats(raw)
        assert result.avg == 1.0
        assert result.obp == 1.0
        assert result.slg == 1.0
        assert result.ops == 2.0
        assert result.iso == 0.0

    def test_null_statcast_data(self):
        """Statcast fields should gracefully handle None."""
        raw = {
            "pa": 50, "ab": 45, "h": 10, "singles": 8, "doubles": 2,
            "triples": 0, "hr": 0, "rbi": 5, "bb": 5, "ibb": 0,
            "hbp": 0, "so": 15, "sf": 0, "sh": 0,
            "avg_exit_velocity": None, "avg_launch_angle": None,
            "hard_hit": 0, "barrels": 0, "batted_balls": 0,
        }
        result = compute_batting_stats(raw)
        assert result.avg_exit_velocity is None
        assert result.avg_launch_angle is None
        assert result.hard_hit_pct is None
        assert result.barrel_pct is None

    def test_none_values_in_raw(self):
        """Raw dict values can be None (from SQL NULL). Should not crash."""
        raw = {
            "pa": 100, "ab": None, "h": None, "singles": None, "doubles": None,
            "triples": None, "hr": None, "rbi": None, "bb": None, "ibb": None,
            "hbp": None, "so": None, "sf": None, "sh": None,
            "avg_exit_velocity": None, "avg_launch_angle": None,
            "hard_hit": None, "barrels": None, "batted_balls": None,
        }
        result = compute_batting_stats(raw)
        assert result.pa == 100
        assert result.ab == 0
        assert result.avg is None


# ---------------------------------------------------------------------------
# Pitching stats computation
# ---------------------------------------------------------------------------


class TestComputePitchingStats:
    """
    Test case: a pitcher who faced 200 batters.

    200 PA: 45 H (10 2B, 2 3B, 5 HR), 20 BB (2 IBB), 3 HBP,
    60 SO, 2 SF, 3 RBI, outs_recorded = 180 (60 IP).
    AB = 200 - 20 - 3 - 2 = 175
    """

    @pytest.fixture
    def raw_pitching(self):
        return {
            "pa": 200,
            "ab": 175,
            "h": 45,
            "singles": 28,
            "doubles": 10,
            "triples": 2,
            "hr": 5,
            "rbi": 3,
            "bb": 20,
            "ibb": 2,
            "hbp": 3,
            "so": 60,
            "sf": 2,
            "sh": 0,
            "avg_exit_velocity": 87.2,
            "avg_launch_angle": 10.5,
            "hard_hit": 30,
            "barrels": 8,
            "batted_balls": 110,
            "outs_recorded": 180,
        }

    def test_innings_pitched_display(self, raw_pitching):
        # 180 outs / 3 = 60.0 IP
        result = compute_pitching_stats(raw_pitching)
        assert result.ip == 60.0

    def test_innings_pitched_partial(self):
        raw = dict(
            pa=10, ab=9, h=2, singles=2, doubles=0, triples=0, hr=0,
            rbi=0, bb=1, ibb=0, hbp=0, so=3, sf=0, sh=0,
            avg_exit_velocity=None, avg_launch_angle=None,
            hard_hit=0, barrels=0, batted_balls=5,
            outs_recorded=7,  # 2.1 IP display, 2.333 decimal
        )
        result = compute_pitching_stats(raw)
        assert result.ip == 2.1  # display format
        assert result.ip_decimal == pytest.approx(7 / 3, abs=0.01)

    def test_whip(self, raw_pitching):
        # WHIP = (H + BB) / IP = (45 + 20) / 60 = 1.0833
        result = compute_pitching_stats(raw_pitching)
        assert result.whip == pytest.approx(1.08, abs=0.01)

    def test_k_per_9(self, raw_pitching):
        # K/9 = 60 * 9 / 60 = 9.0
        result = compute_pitching_stats(raw_pitching)
        assert result.k_per_9 == pytest.approx(9.0, abs=0.1)

    def test_bb_per_9(self, raw_pitching):
        # BB/9 = 20 * 9 / 60 = 3.0
        result = compute_pitching_stats(raw_pitching)
        assert result.bb_per_9 == pytest.approx(3.0, abs=0.1)

    def test_hr_per_9(self, raw_pitching):
        # HR/9 = 5 * 9 / 60 = 0.75
        result = compute_pitching_stats(raw_pitching)
        assert result.hr_per_9 == pytest.approx(0.75, abs=0.1)

    def test_k_percentage(self, raw_pitching):
        # K% = 60 / 200 = 0.300
        result = compute_pitching_stats(raw_pitching)
        assert result.k_pct == pytest.approx(0.300, abs=0.001)

    def test_bb_percentage(self, raw_pitching):
        result = compute_pitching_stats(raw_pitching)
        assert result.bb_pct == pytest.approx(0.100, abs=0.001)

    def test_fip(self, raw_pitching):
        """FIP = (13*HR + 3*(BB+HBP) - 2*SO) / IP + FIP_constant"""
        result = compute_pitching_stats(raw_pitching, season=2024)
        # (13*5 + 3*(20+3) - 2*60) / 60 + 3.22
        # = (65 + 69 - 120) / 60 + 3.22 = 14/60 + 3.22 = 0.2333 + 3.22 = 3.4533
        assert result.fip == pytest.approx(3.45, abs=0.05)

    def test_avg_against(self, raw_pitching):
        # AVG = 45 / 175 = 0.2571
        result = compute_pitching_stats(raw_pitching)
        assert result.avg_against == pytest.approx(0.257, abs=0.001)

    def test_babip_against(self, raw_pitching):
        # BABIP = (H - HR) / (AB - SO - HR + SF) = (45-5)/(175-60-5+2) = 40/112
        result = compute_pitching_stats(raw_pitching)
        assert result.babip_against == pytest.approx(40 / 112, abs=0.001)

    def test_zero_outs_recorded(self):
        """Pitcher with no outs — IP-based stats should be None."""
        raw = {k: 0 for k in [
            "pa", "ab", "h", "singles", "doubles", "triples", "hr", "rbi",
            "bb", "ibb", "hbp", "so", "sf", "sh",
            "hard_hit", "barrels", "batted_balls", "outs_recorded",
        ]}
        raw["avg_exit_velocity"] = None
        raw["avg_launch_angle"] = None
        result = compute_pitching_stats(raw)
        assert result.whip is None
        assert result.k_per_9 is None
        assert result.fip is None


# ---------------------------------------------------------------------------
# Steal stats computation
# ---------------------------------------------------------------------------


class TestComputeStealStats:
    def test_basic_steal_stats(self):
        raw = {"attempts": 30, "stolen_bases": 25, "caught_stealing": 5}
        result = compute_steal_stats(raw)
        assert result.attempts == 30
        assert result.stolen_bases == 25
        assert result.caught_stealing == 5
        assert result.steal_pct == pytest.approx(25 / 30, abs=0.001)

    def test_perfect_steal_record(self):
        raw = {"attempts": 10, "stolen_bases": 10, "caught_stealing": 0}
        result = compute_steal_stats(raw)
        assert result.steal_pct == 1.0

    def test_no_steals(self):
        raw = {"attempts": 0, "stolen_bases": 0, "caught_stealing": 0}
        result = compute_steal_stats(raw)
        assert result.steal_pct is None

    def test_all_caught(self):
        raw = {"attempts": 5, "stolen_bases": 0, "caught_stealing": 5}
        result = compute_steal_stats(raw)
        assert result.steal_pct == 0.0
