from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ZigZagConfig:
    config_id: int
    config_code: str
    model_version: str
    timeframe: str
    deviation_pct: float
    pivot_price_source: str
    confirmation_price_source: str
    minimum_swing_bars: int


@dataclass(frozen=True)
class ZigZagPivot:
    config_id: int
    ticker: str
    pivot_seq: int
    pivot_type: str
    pivot_date: date
    pivot_price: float
    confirmed_at_date: date
    confirmation_price: float
    deviation_pct: float

    def to_record(self) -> tuple[object, ...]:
        return (
            self.config_id,
            self.ticker,
            self.pivot_seq,
            self.pivot_type,
            self.pivot_date,
            self.pivot_price,
            self.confirmed_at_date,
            self.confirmation_price,
            self.deviation_pct,
        )


@dataclass(frozen=True)
class ZigZagCurrentLeg:
    config_id: int
    ticker: str
    as_of_date: date
    direction: str | None
    start_pivot_seq: int | None
    start_pivot_date: date | None
    start_pivot_price: float | None
    candidate_pivot_type: str | None
    candidate_pivot_date: date | None
    candidate_pivot_price: float | None
    last_close: float
    current_move_pct: float | None
    reversal_from_candidate_pct: float | None
    status: str

    def to_record(self) -> tuple[object, ...]:
        return (
            self.config_id,
            self.ticker,
            self.as_of_date,
            self.direction,
            self.start_pivot_seq,
            self.start_pivot_date,
            self.start_pivot_price,
            self.candidate_pivot_type,
            self.candidate_pivot_date,
            self.candidate_pivot_price,
            self.last_close,
            self.current_move_pct,
            self.reversal_from_candidate_pct,
            self.status,
        )
