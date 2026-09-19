from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PriceMovementConfig:
    config_id: int
    config_code: str
    model_version: str
    timeframe: str
    zigzag_config_code: str
    profile_lookback_swings: int
    minimum_profile_swings: int
    trend_bias_threshold: float
    range_bias_threshold: float
    efficiency_threshold: float
    atr_period: int


@dataclass(frozen=True)
class PriceMovementSwing:
    price_movement_config_id: int
    zigzag_config_id: int
    zigzag_config_code: str
    ticker: str
    swing_seq: int
    direction: str
    start_pivot_seq: int
    start_date: date
    start_price: float
    end_pivot_seq: int
    end_date: date
    end_price: float
    confirmed_at_date: date
    swing_pct: float
    trading_bars: int
    calendar_days: int
    velocity_pct_per_bar: float
    avg_atr_pct: float | None
    atr_normalized_move: float | None
    path_efficiency: float
    directional_persistence_rate: float

    def to_record(self) -> tuple[object, ...]:
        return (
            self.price_movement_config_id,
            self.zigzag_config_id,
            self.zigzag_config_code,
            self.ticker,
            self.swing_seq,
            self.direction,
            self.start_pivot_seq,
            self.start_date,
            self.start_price,
            self.end_pivot_seq,
            self.end_date,
            self.end_price,
            self.confirmed_at_date,
            self.swing_pct,
            self.trading_bars,
            self.calendar_days,
            self.velocity_pct_per_bar,
            self.avg_atr_pct,
            self.atr_normalized_move,
            self.path_efficiency,
            self.directional_persistence_rate,
        )


@dataclass(frozen=True)
class PriceMovementProfile:
    price_movement_config_id: int
    zigzag_config_id: int
    zigzag_config_code: str
    ticker: str
    as_of_confirmed_at_date: date
    profile_lookback_swings: int
    confirmed_swing_count: int
    last_swing_seq: int
    last_swing_direction: str
    last_swing_pct: float
    median_up_swing_pct: float | None
    median_down_swing_abs_pct: float | None
    median_abs_swing_pct: float
    median_trading_bars: float
    median_abs_velocity_pct_per_bar: float
    median_atr_normalized_move: float | None
    median_path_efficiency: float
    median_directional_persistence_rate: float
    directional_bias: float
    movement_character: str

    def to_record(self) -> tuple[object, ...]:
        return (
            self.price_movement_config_id,
            self.zigzag_config_id,
            self.zigzag_config_code,
            self.ticker,
            self.as_of_confirmed_at_date,
            self.profile_lookback_swings,
            self.confirmed_swing_count,
            self.last_swing_seq,
            self.last_swing_direction,
            self.last_swing_pct,
            self.median_up_swing_pct,
            self.median_down_swing_abs_pct,
            self.median_abs_swing_pct,
            self.median_trading_bars,
            self.median_abs_velocity_pct_per_bar,
            self.median_atr_normalized_move,
            self.median_path_efficiency,
            self.median_directional_persistence_rate,
            self.directional_bias,
            self.movement_character,
        )
