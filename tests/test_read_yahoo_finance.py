import pytest

from src.CrawlStock.readYahooFinance import _build_download_kwargs


def test_daily_download_window_uses_period() -> None:
    kwargs, label = _build_download_kwargs(from_last_day=15)

    assert kwargs == {"period": "15d"}
    assert label == "period=15d"


def test_historical_download_window_uses_start_and_exclusive_end() -> None:
    kwargs, label = _build_download_kwargs(
        from_last_day=15,
        start_date="2024-04-01",
        end_date="2024-05-01",
    )

    assert kwargs == {"start": "2024-04-01", "end": "2024-05-01"}
    assert label == "start=2024-04-01 | end(exclusive)=2024-05-01"


def test_historical_download_window_to_latest_ignores_checkpoint_period() -> None:
    kwargs, label = _build_download_kwargs(
        from_last_day=3,
        start_date="2024-04-01",
    )

    assert kwargs == {"start": "2024-04-01"}
    assert label == "start=2024-04-01"


def test_end_date_requires_start_date() -> None:
    with pytest.raises(ValueError, match="end_date requires start_date"):
        _build_download_kwargs(end_date="2024-05-01")


def test_end_date_must_be_later_than_start_date() -> None:
    with pytest.raises(ValueError, match="end_date must be later than start_date"):
        _build_download_kwargs(
            start_date="2024-04-01",
            end_date="2024-04-01",
        )
