from __future__ import annotations

from statistics import median

import numpy as np
import pandas as pd

from cherrystock.domain.analytics.price_movement.classifier import classify_movement
from cherrystock.domain.analytics.price_movement.models import (
    PriceMovementConfig,
    PriceMovementProfile,
    PriceMovementSwing,
)


_ZIGZAG_REQUIRED = {
    "ConfigId",
    "ConfigCode",
    "Ticker",
    "SwingSeq",
    "Direction",
    "StartPivotSeq",
    "StartDate",
    "StartPrice",
    "EndPivotSeq",
    "EndDate",
    "EndPrice",
    "ConfirmedAtDate",
    "SwingPct",
}

_OHLC_REQUIRED = {"Date", "High", "Low", "Close"}


def _prepare_ohlc(frame: pd.DataFrame, *, atr_period: int) -> pd.DataFrame:
    missing = _OHLC_REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(f"Price Movement OHLC is missing columns: {sorted(missing)}")
    if atr_period < 2:
        raise ValueError("atr_period must be >= 2.")

    data = frame.loc[:, ["Date", "High", "Low", "Close"]].copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    for column in ("High", "Low", "Close"):
        data[column] = pd.to_numeric(data[column], errors="coerce")

    numeric = data[["High", "Low", "Close"]]
    valid = (
        data["Date"].notna()
        & np.isfinite(numeric).all(axis=1)
        & (data["High"] > 0)
        & (data["Low"] > 0)
        & (data["Close"] > 0)
        & (data["High"] >= data["Low"])
        & (data["Close"] <= data["High"])
        & (data["Close"] >= data["Low"])
    )
    data = data.loc[valid].sort_values("Date").reset_index(drop=True)

    if data.empty:
        raise ValueError("Price Movement OHLC has no usable rows.")
    if data["Date"].duplicated().any():
        raise ValueError("Price Movement OHLC contains duplicate dates.")

    previous_close = data["Close"].shift(1)
    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - previous_close).abs(),
            (data["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    data["TrueRange"] = true_range.astype(float)
    data["ATR"] = data["TrueRange"].rolling(
        window=atr_period,
        min_periods=atr_period,
    ).mean()
    data["ATRPct"] = data["ATR"] / data["Close"]
    data["CloseReturn"] = data["Close"].pct_change()
    return data


def _prepare_zigzag_swings(frame: pd.DataFrame) -> pd.DataFrame:
    missing = _ZIGZAG_REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            f"Price Movement ZigZag swings are missing columns: {sorted(missing)}"
        )

    data = frame.copy()
    for column in ("StartDate", "EndDate", "ConfirmedAtDate"):
        data[column] = pd.to_datetime(data[column], errors="coerce")

    numeric_columns = (
        "ConfigId",
        "SwingSeq",
        "StartPivotSeq",
        "StartPrice",
        "EndPivotSeq",
        "EndPrice",
        "SwingPct",
    )
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    if data[
        [
            "StartDate",
            "EndDate",
            "ConfirmedAtDate",
            *numeric_columns,
        ]
    ].isna().any().any():
        raise ValueError("Price Movement ZigZag input contains NULL/invalid required values.")

    data = data.sort_values(["ConfigId", "Ticker", "SwingSeq"]).reset_index(drop=True)

    if data.duplicated(subset=["ConfigId", "Ticker", "SwingSeq"]).any():
        raise ValueError("Price Movement ZigZag input contains duplicate swing identity.")

    return data


def build_price_movement_swings(
    zigzag_swings: pd.DataFrame,
    ohlc: pd.DataFrame,
    *,
    config: PriceMovementConfig,
) -> list[PriceMovementSwing]:
    if zigzag_swings.empty:
        return []

    swings = _prepare_zigzag_swings(zigzag_swings)
    path_data = _prepare_ohlc(ohlc, atr_period=config.atr_period)

    output: list[PriceMovementSwing] = []

    for row in swings.itertuples(index=False):
        start_date = row.StartDate.date()
        end_date = row.EndDate.date()
        confirmed_at_date = row.ConfirmedAtDate.date()

        if not start_date < end_date:
            raise ValueError(
                f"invalid swing dates for {row.Ticker} seq={int(row.SwingSeq)}"
            )
        if not end_date < confirmed_at_date:
            raise ValueError(
                f"EndDate must be before ConfirmedAtDate for {row.Ticker} "
                f"seq={int(row.SwingSeq)}"
            )

        segment = path_data.loc[
            (path_data["Date"].dt.date >= start_date)
            & (path_data["Date"].dt.date <= end_date)
        ].copy()

        if segment.empty:
            raise ValueError(
                f"missing OHLC segment for {row.Ticker} seq={int(row.SwingSeq)}"
            )

        actual_start = segment.iloc[0]["Date"].date()
        actual_end = segment.iloc[-1]["Date"].date()
        if actual_start != start_date or actual_end != end_date:
            raise ValueError(
                f"OHLC endpoint missing for {row.Ticker} seq={int(row.SwingSeq)}: "
                f"expected {start_date}->{end_date}, got {actual_start}->{actual_end}"
            )

        trading_bars = len(segment) - 1
        if trading_bars < 1:
            raise ValueError(
                f"TradingBars must be >= 1 for {row.Ticker} seq={int(row.SwingSeq)}"
            )

        start_price = float(row.StartPrice)
        end_price = float(row.EndPrice)
        swing_pct = end_price / start_price - 1.0
        upstream_swing_pct = float(row.SwingPct)
        if not np.isclose(swing_pct, upstream_swing_pct, rtol=1e-9, atol=1e-9):
            raise ValueError(
                f"ZigZag SwingPct mismatch for {row.Ticker} seq={int(row.SwingSeq)}: "
                f"upstream={upstream_swing_pct} computed={swing_pct}"
            )

        direction = str(row.Direction)
        if direction == "UP" and swing_pct <= 0:
            raise ValueError(
                f"UP swing is not positive for {row.Ticker} seq={int(row.SwingSeq)}"
            )
        if direction == "DOWN" and swing_pct >= 0:
            raise ValueError(
                f"DOWN swing is not negative for {row.Ticker} seq={int(row.SwingSeq)}"
            )
        if direction not in {"UP", "DOWN"}:
            raise ValueError(
                f"unsupported direction {direction} for {row.Ticker} "
                f"seq={int(row.SwingSeq)}"
            )

        velocity = swing_pct / trading_bars

        atr_values = segment["ATRPct"].replace([np.inf, -np.inf], np.nan).dropna()
        avg_atr_pct = float(atr_values.mean()) if not atr_values.empty else None
        atr_normalized = (
            abs(swing_pct) / avg_atr_pct
            if avg_atr_pct is not None and avg_atr_pct > 0
            else None
        )

        true_range_sum = float(segment["TrueRange"].sum())
        path_efficiency = (
            abs(end_price - start_price) / true_range_sum
            if true_range_sum > 0
            else 0.0
        )
        path_efficiency = float(np.clip(path_efficiency, 0.0, 1.0))

        interval_returns = segment["CloseReturn"].iloc[1:].dropna()
        if interval_returns.empty:
            persistence = 0.0
        elif direction == "UP":
            persistence = float((interval_returns > 0).mean())
        else:
            persistence = float((interval_returns < 0).mean())
        persistence = float(np.clip(persistence, 0.0, 1.0))

        output.append(
            PriceMovementSwing(
                price_movement_config_id=config.config_id,
                zigzag_config_id=int(row.ConfigId),
                zigzag_config_code=str(row.ConfigCode),
                ticker=str(row.Ticker),
                swing_seq=int(row.SwingSeq),
                direction=direction,
                start_pivot_seq=int(row.StartPivotSeq),
                start_date=start_date,
                start_price=start_price,
                end_pivot_seq=int(row.EndPivotSeq),
                end_date=end_date,
                end_price=end_price,
                confirmed_at_date=confirmed_at_date,
                swing_pct=float(swing_pct),
                trading_bars=int(trading_bars),
                calendar_days=(end_date - start_date).days,
                velocity_pct_per_bar=float(velocity),
                avg_atr20_pct=avg_atr_pct,
                atr_normalized_move=(
                    float(atr_normalized) if atr_normalized is not None else None
                ),
                path_efficiency=path_efficiency,
                directional_persistence_rate=persistence,
            )
        )

    return output


def _optional_median(values: list[float | None]) -> float | None:
    finite = [
        float(value)
        for value in values
        if value is not None and np.isfinite(float(value))
    ]
    return float(median(finite)) if finite else None


def build_price_movement_profile(
    swings: list[PriceMovementSwing],
    *,
    config: PriceMovementConfig,
) -> PriceMovementProfile | None:
    if not swings:
        return None

    ordered = sorted(swings, key=lambda item: item.swing_seq)
    recent = ordered[-config.profile_lookback_swings :]

    identities = {
        (item.zigzag_config_id, item.zigzag_config_code, item.ticker)
        for item in recent
    }
    if len(identities) != 1:
        raise ValueError("Price Movement profile input must belong to one ZigZag config/ticker.")

    swing_values = [float(item.swing_pct) for item in recent]
    total_abs = sum(abs(value) for value in swing_values)
    directional_bias = (
        sum(swing_values) / total_abs
        if total_abs > 0
        else 0.0
    )
    directional_bias = float(np.clip(directional_bias, -1.0, 1.0))

    up_values = [item.swing_pct for item in recent if item.direction == "UP"]
    down_abs_values = [
        abs(item.swing_pct) for item in recent if item.direction == "DOWN"
    ]
    median_efficiency = float(median(item.path_efficiency for item in recent))

    movement_character = classify_movement(
        confirmed_swing_count=len(recent),
        directional_bias=directional_bias,
        median_path_efficiency=median_efficiency,
        config=config,
    )

    last = recent[-1]
    return PriceMovementProfile(
        price_movement_config_id=config.config_id,
        zigzag_config_id=last.zigzag_config_id,
        zigzag_config_code=last.zigzag_config_code,
        ticker=last.ticker,
        as_of_confirmed_at_date=max(item.confirmed_at_date for item in recent),
        profile_lookback_swings=config.profile_lookback_swings,
        confirmed_swing_count=len(recent),
        last_swing_seq=last.swing_seq,
        last_swing_direction=last.direction,
        last_swing_pct=last.swing_pct,
        median_up_swing_pct=_optional_median(up_values),
        median_down_swing_abs_pct=_optional_median(down_abs_values),
        median_abs_swing_pct=float(median(abs(value) for value in swing_values)),
        median_trading_bars=float(median(item.trading_bars for item in recent)),
        median_abs_velocity_pct_per_bar=float(
            median(abs(item.velocity_pct_per_bar) for item in recent)
        ),
        median_atr_normalized_move=_optional_median(
            [item.atr_normalized_move for item in recent]
        ),
        median_path_efficiency=median_efficiency,
        median_directional_persistence_rate=float(
            median(item.directional_persistence_rate for item in recent)
        ),
        directional_bias=directional_bias,
        movement_character=movement_character,
    )


def calculate_price_movement(
    zigzag_swings: pd.DataFrame,
    ohlc: pd.DataFrame,
    *,
    config: PriceMovementConfig,
) -> tuple[list[PriceMovementSwing], PriceMovementProfile | None]:
    swings = build_price_movement_swings(
        zigzag_swings,
        ohlc,
        config=config,
    )
    profile = build_price_movement_profile(swings, config=config)
    return swings, profile
