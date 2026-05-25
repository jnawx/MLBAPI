"""
Stats engine — computes derived statistics from raw aggregate counts.

The query builder returns raw counting stats (PA, AB, H, etc.) from the database.
This module takes those raw numbers and computes rate stats (AVG, OBP, SLG, wOBA, etc.).
"""

from __future__ import annotations

from typing import Any, Optional

from app.schemas.stats import BattingStatLine, PitchingStatLine, StealStatLine

# ---------------------------------------------------------------------------
# wOBA weights by season (source: FanGraphs)
# ---------------------------------------------------------------------------

WOBA_WEIGHTS: dict[int, dict[str, float]] = {
    2021: {"wBB": 0.692, "wHBP": 0.722, "w1B": 0.879, "w2B": 1.242, "w3B": 1.568, "wHR": 2.015, "wOBAScale": 1.256},
    2022: {"wBB": 0.689, "wHBP": 0.720, "w1B": 0.884, "w2B": 1.261, "w3B": 1.601, "wHR": 2.072, "wOBAScale": 1.282},
    2023: {"wBB": 0.696, "wHBP": 0.726, "w1B": 0.883, "w2B": 1.244, "w3B": 1.569, "wHR": 2.015, "wOBAScale": 1.248},
    2024: {"wBB": 0.697, "wHBP": 0.727, "w1B": 0.885, "w2B": 1.248, "w3B": 1.577, "wHR": 2.025, "wOBAScale": 1.255},
    # 2025+ use 2024 weights as estimates until FanGraphs publishes actuals
}

# FIP constant by season (approximate, derived from league ERA - lgFIP)
FIP_CONSTANTS: dict[int, float] = {
    2021: 3.17,
    2022: 3.26,
    2023: 3.25,
    2024: 3.22,
}

DEFAULT_WOBA_WEIGHTS = WOBA_WEIGHTS[2024]
DEFAULT_FIP_CONSTANT = 3.22


def _safe_div(numerator: float, denominator: float) -> Optional[float]:
    """Safely divide, returning None instead of dividing by zero."""
    if denominator == 0:
        return None
    return numerator / denominator


def _round_stat(value: Optional[float], digits: int = 3) -> Optional[float]:
    """Round a stat to a fixed number of digits, preserving None."""
    if value is None:
        return None
    return round(value, digits)


def _get_woba_weights(season: Optional[int] = None) -> dict[str, float]:
    """Get wOBA weights for a season, falling back to defaults."""
    if season and season in WOBA_WEIGHTS:
        return WOBA_WEIGHTS[season]
    return DEFAULT_WOBA_WEIGHTS


# ---------------------------------------------------------------------------
# Batting stats computation
# ---------------------------------------------------------------------------


def compute_batting_stats(raw: dict[str, Any], season: Optional[int] = None) -> BattingStatLine:
    """
    Compute all batting statistics from raw aggregate counts.

    Parameters
    ----------
    raw : dict
        Raw counting stats from the database query. Keys match the labels
        in the query builder's aggregate columns.
    season : int, optional
        Season for wOBA weight lookup. If querying multiple seasons, pass None
        to use default weights.

    Returns
    -------
    BattingStatLine
    """
    pa = int(raw.get("pa", 0) or 0)
    ab = int(raw.get("ab", 0) or 0)
    h = int(raw.get("h", 0) or 0)
    singles = int(raw.get("singles", 0) or 0)
    doubles = int(raw.get("doubles", 0) or 0)
    triples = int(raw.get("triples", 0) or 0)
    hr = int(raw.get("hr", 0) or 0)
    rbi = int(raw.get("rbi", 0) or 0)
    bb = int(raw.get("bb", 0) or 0)
    ibb = int(raw.get("ibb", 0) or 0)
    hbp = int(raw.get("hbp", 0) or 0)
    so = int(raw.get("so", 0) or 0)
    sf = int(raw.get("sf", 0) or 0)
    sh = int(raw.get("sh", 0) or 0)
    batted_balls = int(raw.get("batted_balls", 0) or 0)
    hard_hit = int(raw.get("hard_hit", 0) or 0)
    barrels = int(raw.get("barrels", 0) or 0)

    # Total bases: 1B + 2*2B + 3*3B + 4*HR = H + 2B + 2*3B + 3*HR
    tb = h + doubles + 2 * triples + 3 * hr

    # Rate stats
    avg = _safe_div(h, ab)
    obp_denom = ab + bb + hbp + sf
    obp = _safe_div(h + bb + hbp, obp_denom)
    slg = _safe_div(tb, ab)
    ops = (obp or 0) + (slg or 0) if obp is not None and slg is not None else None
    iso = (slg or 0) - (avg or 0) if slg is not None and avg is not None else None

    babip_denom = ab - so - hr + sf
    babip = _safe_div(h - hr, babip_denom)

    k_pct = _safe_div(so, pa)
    bb_pct = _safe_div(bb, pa)
    hr_per_pa = _safe_div(hr, pa)

    # wOBA
    w = _get_woba_weights(season)
    woba_num = (
        w["wBB"] * (bb - ibb) + w["wHBP"] * hbp + w["w1B"] * singles
        + w["w2B"] * doubles + w["w3B"] * triples + w["wHR"] * hr
    )
    woba_denom = ab + bb - ibb + sf + hbp
    woba = _safe_div(woba_num, woba_denom)

    # Statcast
    avg_ev = raw.get("avg_exit_velocity")
    avg_la = raw.get("avg_launch_angle")
    hard_hit_pct = _safe_div(hard_hit, batted_balls)
    barrel_pct = _safe_div(barrels, batted_balls)

    return BattingStatLine(
        pa=pa,
        ab=ab,
        h=h,
        singles=singles,
        doubles=doubles,
        triples=triples,
        hr=hr,
        rbi=rbi,
        bb=bb,
        ibb=ibb,
        hbp=hbp,
        so=so,
        sf=sf,
        sh=sh,
        avg=_round_stat(avg),
        obp=_round_stat(obp),
        slg=_round_stat(slg),
        ops=_round_stat(ops),
        iso=_round_stat(iso),
        babip=_round_stat(babip),
        woba=_round_stat(woba),
        k_pct=_round_stat(k_pct),
        bb_pct=_round_stat(bb_pct),
        hr_per_pa=_round_stat(hr_per_pa),
        avg_exit_velocity=_round_stat(float(avg_ev), 1) if avg_ev is not None else None,
        avg_launch_angle=_round_stat(float(avg_la), 1) if avg_la is not None else None,
        hard_hit_pct=_round_stat(hard_hit_pct),
        barrel_pct=_round_stat(barrel_pct),
        batted_balls=batted_balls,
    )


# ---------------------------------------------------------------------------
# Pitching stats computation
# ---------------------------------------------------------------------------


def compute_pitching_stats(raw: dict[str, Any], season: Optional[int] = None) -> PitchingStatLine:
    """Compute all pitching statistics from raw aggregate counts."""
    pa = int(raw.get("pa", 0) or 0)
    ab = int(raw.get("ab", 0) or 0)
    h = int(raw.get("h", 0) or 0)
    hr = int(raw.get("hr", 0) or 0)
    bb = int(raw.get("bb", 0) or 0)
    ibb = int(raw.get("ibb", 0) or 0)
    hbp = int(raw.get("hbp", 0) or 0)
    so = int(raw.get("so", 0) or 0)
    sf = int(raw.get("sf", 0) or 0)
    rbi = int(raw.get("rbi", 0) or 0)
    outs_recorded = int(raw.get("outs_recorded", 0) or 0)
    batted_balls = int(raw.get("batted_balls", 0) or 0)
    hard_hit = int(raw.get("hard_hit", 0) or 0)

    # Innings pitched
    full_innings = outs_recorded // 3
    partial = outs_recorded % 3
    ip_display = float(f"{full_innings}.{partial}")  # e.g. 6.2 = 6 and 2/3
    ip_decimal = outs_recorded / 3.0

    # Rate stats
    whip = _safe_div(h + bb, ip_decimal)
    k_per_9 = _safe_div(so * 9, ip_decimal)
    bb_per_9 = _safe_div(bb * 9, ip_decimal)
    hr_per_9 = _safe_div(hr * 9, ip_decimal)
    k_pct = _safe_div(so, pa)
    bb_pct = _safe_div(bb, pa)

    # FIP
    fip_constant = FIP_CONSTANTS.get(season, DEFAULT_FIP_CONSTANT) if season else DEFAULT_FIP_CONSTANT
    fip_core = _safe_div(13 * hr + 3 * (bb + hbp) - 2 * so, ip_decimal)
    fip = fip_core + fip_constant if fip_core is not None else None

    # Opponent slash line
    avg_against = _safe_div(h, ab)
    obp_denom = ab + bb + hbp + sf
    obp_against = _safe_div(h + bb + hbp, obp_denom)

    singles = h - int(raw.get("doubles", 0) or 0) - int(raw.get("triples", 0) or 0) - hr
    doubles = int(raw.get("doubles", 0) or 0)
    triples = int(raw.get("triples", 0) or 0)
    tb = h + doubles + 2 * triples + 3 * hr
    slg_against = _safe_div(tb, ab)

    babip_denom = ab - so - hr + sf
    babip_against = _safe_div(h - hr, babip_denom)

    # Statcast
    avg_ev = raw.get("avg_exit_velocity")
    avg_la = raw.get("avg_launch_angle")
    hard_hit_pct = _safe_div(hard_hit, batted_balls)

    return PitchingStatLine(
        pa=pa,
        ab=ab,
        h=h,
        hr=hr,
        bb=bb,
        ibb=ibb,
        hbp=hbp,
        so=so,
        sf=sf,
        rbi=rbi,
        outs_recorded=outs_recorded,
        ip=ip_display,
        ip_decimal=_round_stat(ip_decimal, 2),
        whip=_round_stat(whip, 2),
        k_per_9=_round_stat(k_per_9, 2),
        bb_per_9=_round_stat(bb_per_9, 2),
        hr_per_9=_round_stat(hr_per_9, 2),
        k_pct=_round_stat(k_pct),
        bb_pct=_round_stat(bb_pct),
        fip=_round_stat(fip, 2),
        avg_against=_round_stat(avg_against),
        obp_against=_round_stat(obp_against),
        slg_against=_round_stat(slg_against),
        babip_against=_round_stat(babip_against),
        avg_exit_velocity=_round_stat(float(avg_ev), 1) if avg_ev is not None else None,
        avg_launch_angle=_round_stat(float(avg_la), 1) if avg_la is not None else None,
        hard_hit_pct=_round_stat(hard_hit_pct),
    )


# ---------------------------------------------------------------------------
# Steal stats computation
# ---------------------------------------------------------------------------


def compute_steal_stats(raw: dict[str, Any]) -> StealStatLine:
    """Compute stolen base statistics."""
    attempts = int(raw.get("attempts", 0) or 0)
    sb = int(raw.get("stolen_bases", 0) or 0)
    cs = int(raw.get("caught_stealing", 0) or 0)
    pct = _safe_div(sb, attempts)

    return StealStatLine(
        attempts=attempts,
        stolen_bases=sb,
        caught_stealing=cs,
        steal_pct=_round_stat(pct),
    )
