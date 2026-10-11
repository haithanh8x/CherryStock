"""Focused P0-P2 Volume Profile tests: data gate, score, explainability and UI."""
from dataclasses import replace
from datetime import date

import pandas as pd
import pytest

from src.calcEngine.volumeProfile import (
    VolumeProfileConfig,
    build_volume_profile_from_history,
    build_volume_profile_from_intraday_history,
)
from src.calcEngine.levelLadder import (
    ConfirmationContext,
    CurrentPrice,
    LevelCandidate,
    SOURCE_FAMILY_TREND_AVERAGE,
    SOURCE_FAMILY_VOLUME_CONFIRMATION,
    SOURCE_FAMILY_VOLUME_STRUCTURE,
    StrengthConfig,
    build_level_ladder_from_data,
)
from src.Chart.levelLadderChart import ladder_tree_nodes


AS_OF = date(2026, 3, 31)


def _intraday_fixture():
    days = pd.bdate_range("2026-01-05", periods=50)
    frames = []
    daily = []
    for day in days:
        daily.append({"Date": day, "Volume": 600.0})
        for index in range(6):
            frames.append({
                "DateTime": day + pd.Timedelta(minutes=index),
                "High": 101.0 + (index % 2) * 0.5,
                "Low": 99.0 + (index % 2) * 0.5,
                "Volume": 100.0,
            })
    return pd.DataFrame(frames), pd.DataFrame(daily)


def test_intraday_profile_is_opt_in_and_eod_coverage_gated():
    intraday, daily = _intraday_fixture()
    config = VolumeProfileConfig(source_mode="INTRADAY", window_bars=40,
                                 min_intraday_sessions=30, bins=24)
    profile = build_volume_profile_from_intraday_history(
        intraday, as_of_date=AS_OF, daily_volume=daily, config=config,
    )
    assert profile.source_resolution == "INTRADAY_BAR_APPROX"
    assert profile.eligible_sessions == 40
    assert profile.bars == 40 * 6
    assert profile.total_volume == pytest.approx(40 * 600)
    assert profile.window_end <= AS_OF


def test_intraday_future_rows_never_leak_into_profile():
    intraday, daily = _intraday_fixture()
    config = VolumeProfileConfig(source_mode="INTRADAY", window_bars=40,
                                 min_intraday_sessions=30)
    base = build_volume_profile_from_intraday_history(
        intraday, as_of_date=AS_OF, daily_volume=daily, config=config,
    )
    future = pd.DataFrame([{
        "DateTime": pd.Timestamp("2027-01-01 10:00"),
        "High": 9999.0, "Low": 9998.0, "Volume": 9e8,
    }])
    extended = build_volume_profile_from_intraday_history(
        pd.concat([intraday, future], ignore_index=True),
        as_of_date=AS_OF, daily_volume=daily, config=config,
    )
    assert extended == base


def test_incomplete_or_cumulative_intraday_volume_is_rejected():
    intraday, daily = _intraday_fixture()
    daily["Volume"] = 6000.0  # 10x volume cannot pass EOD coverage check
    with pytest.raises(ValueError, match="volume-validated intraday sessions"):
        build_volume_profile_from_intraday_history(
            intraday, as_of_date=AS_OF, daily_volume=daily,
            config=VolumeProfileConfig(source_mode="INTRADAY"),
        )


def test_daily_volume_profile_does_not_accept_nonfinite_volume():
    daily = pd.DataFrame([
        {"Date": day, "Low": 95.0, "High": 105.0, "Volume": 100.0}
        for day in pd.bdate_range("2026-01-02", periods=40)
    ])
    daily.loc[0, "Volume"] = float("inf")
    profile = build_volume_profile_from_history(
        daily, as_of_date=AS_OF, config=VolumeProfileConfig(min_records=30),
    )
    assert profile.bars == 39
    assert profile.total_volume == pytest.approx(3900.0)


def _level(price=95.0, *, volume=False):
    return LevelCandidate(
        ticker="MWG", price=price, source_type="VOLUME_PROFILE" if volume else "INDICATOR",
        source_code="VP_HVN_01" if volume else "MA20_D", timeframe="D",
        indicator_code=None if volume else "MA", config_id=None if volume else 2,
        config_code=None if volume else "MA20_D",
        component_code="HVN" if volume else "VALUE", source_date=AS_OF,
        confirmed_at=AS_OF, source_family=(
            SOURCE_FAMILY_VOLUME_STRUCTURE if volume else SOURCE_FAMILY_TREND_AVERAGE
        ),
        metadata={"volume_share": 0.08, "relative_volume": 1.9,
                  "profile_source": "INTRADAY_BAR_APPROX"} if volume
        else {"length": 20},
    )


def _confirmation():
    return ConfirmationContext(
        ticker="MWG", as_of_date=AS_OF, source_code="VP_HVN_01_CONF",
        source_family=SOURCE_FAMILY_VOLUME_CONFIRMATION,
        timeframe="D", indicator_code="VOLUME_PROFILE",
        config_id=0, config_code="VOLUME_PROFILE", component_code="HVN",
        value=90.0, source_date=AS_OF, reference_price=95.20,
        metadata={"volume_share": 0.08, "profile_source": "INTRADAY_BAR_APPROX"},
    )


def test_distance_aware_challenger_limits_duplicate_volume_evidence():
    current = CurrentPrice("MWG", AS_OF, 100.0)
    kwargs = dict(
        current_price=current,
        candidates=[_level(), _level(volume=True)],
        confirmations=[_confirmation()],
    )
    base = build_level_ladder_from_data(**kwargs)
    legacy = build_level_ladder_from_data(
        **kwargs, strength_config=StrengthConfig(volume_confirmation_mode="LEGACY"),
    )
    challenger = build_level_ladder_from_data(
        **kwargs, strength_config=StrengthConfig(volume_confirmation_mode="DISTANCE_AWARE"),
    )
    assert base == legacy  # production default stays equivalent
    assert [v.price for v in challenger.support_levels] == [
        v.price for v in legacy.support_levels
    ]
    assert challenger.support_levels[0].volume_confirmation_score < 90.0
    assert challenger.support_levels[0].volume_node_type == "HVN"
    assert challenger.support_levels[0].volume_share_pct == pytest.approx(8.0)
    assert challenger.support_levels[0].volume_profile_source == "INTRADAY_BAR_APPROX"
    assert challenger.support_levels[0].volume_score_contribution < (
        legacy.support_levels[0].volume_score_contribution
    )


def test_volume_score_is_exposed_in_tree_without_changing_display_threshold():
    result = build_level_ladder_from_data(
        CurrentPrice("MWG", AS_OF, 100.0), [_level(volume=True)],
        confirmations=[_confirmation()],
    )
    strong = replace(result.support_levels[0], strength_score=85.0)
    visible = replace(result, support_levels=(strong,), nearest_support=strong)
    tree = ladder_tree_nodes(visible)
    assert len(tree) == 1
    assert "VP HVN" in tree[0]["volume_label"]
    assert any("Volume Profile" in x["label"] for x in tree[0]["children"])
    source_details = tree[0]["children"][0]["children"][0]["children"]
    assert any("Volume share: 8.00%" in x["label"] for x in source_details)
    assert any("INTRADAY_BAR_APPROX" in x["label"] for x in source_details)
    assert ladder_tree_nodes(result) == []  # <=80 visual filter untouched


def test_invalid_profile_mode_is_rejected():
    intraday, daily = _intraday_fixture()
    with pytest.raises(ValueError, match="source_mode"):
        build_volume_profile_from_intraday_history(
            intraday, as_of_date=AS_OF, daily_volume=daily,
            config=VolumeProfileConfig(source_mode="TICK"),
        )


def test_intraday_latest_session_and_window_coverage_fail_closed():
    intraday, daily = _intraday_fixture()
    latest = intraday["DateTime"].dt.normalize().max()
    stale = intraday.loc[intraday["DateTime"].dt.normalize() < latest]
    with pytest.raises(ValueError, match="stale intraday profile"):
        build_volume_profile_from_intraday_history(
            stale, as_of_date=AS_OF, daily_volume=daily,
            config=VolumeProfileConfig(source_mode="INTRADAY", window_bars=40),
        )
    # 25/40 valid dates is not a reliable profile, even if >= min_intraday_sessions
    sparse_dates = pd.to_datetime(daily["Date"].tail(40).iloc[::2])
    sparse = intraday.loc[intraday["DateTime"].dt.normalize().isin(sparse_dates)]
    with pytest.raises(ValueError, match="insufficient volume-validated intraday sessions"):
        build_volume_profile_from_intraday_history(
            sparse, as_of_date=AS_OF, daily_volume=daily,
            config=VolumeProfileConfig(
                source_mode="INTRADAY", window_bars=40,
                min_intraday_sessions=10,
            ),
        )
