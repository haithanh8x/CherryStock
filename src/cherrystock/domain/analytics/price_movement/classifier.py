from __future__ import annotations

from cherrystock.domain.analytics.price_movement.models import PriceMovementConfig


ALLOWED_MOVEMENT_CHARACTERS = {
    "INSUFFICIENT_HISTORY",
    "TRENDING_UP",
    "TRENDING_DOWN",
    "RANGE_BOUND",
    "MIXED",
}


def classify_movement(
    *,
    confirmed_swing_count: int,
    directional_bias: float,
    median_path_efficiency: float,
    config: PriceMovementConfig,
) -> str:
    if confirmed_swing_count < config.minimum_profile_swings:
        return "INSUFFICIENT_HISTORY"

    if (
        directional_bias >= config.trend_bias_threshold
        and median_path_efficiency >= config.efficiency_threshold
    ):
        return "TRENDING_UP"

    if (
        directional_bias <= -config.trend_bias_threshold
        and median_path_efficiency >= config.efficiency_threshold
    ):
        return "TRENDING_DOWN"

    if (
        abs(directional_bias) < config.range_bias_threshold
        and median_path_efficiency < config.efficiency_threshold
    ):
        return "RANGE_BOUND"

    return "MIXED"
