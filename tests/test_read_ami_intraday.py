import struct
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from CrawlStock.readAmi import read_amibroker_intraday_dat  # noqa: E402


RECORD_FORMAT = "<iiffffff"


def _write_records(path: Path, records: list[tuple]) -> None:
    with path.open("wb") as handle:
        for record in records:
            handle.write(struct.pack(RECORD_FORMAT, *record))


def test_read_intraday_keeps_duplicate_timestamp_ticks(tmp_path: Path) -> None:
    file_path = tmp_path / "FPT.dat"
    _write_records(
        file_path,
        [
            (20260904, 91530, 72.5, 72.5, 72.5, 72.5, 100.0, 1.0),
            (20260904, 91530, 72.6, 72.6, 72.6, 72.6, 200.0, 2.0),
            (20260904, 91531, 72.7, 72.7, 72.7, 72.7, 300.0, 3.0),
        ],
    )

    result = read_amibroker_intraday_dat(file_path)

    assert len(result) == 3
    assert result["TickSeq"].tolist() == [0, 1, 0]
    assert result["RawTime"].tolist() == [91530, 91530, 91531]
    assert result["Volume"].tolist() == [100, 200, 300]
    assert result["OpenInt"].tolist() == [1.0, 2.0, 3.0]
    assert result["DateTime"].tolist() == [
        pd.Timestamp("2026-09-04 09:15:30"),
        pd.Timestamp("2026-09-04 09:15:30"),
        pd.Timestamp("2026-09-04 09:15:31"),
    ]


def test_read_intraday_supports_millisecond_raw_time(tmp_path: Path) -> None:
    file_path = tmp_path / "VN30F1M.dat"
    _write_records(
        file_path,
        [
            (20260904, 91530123, 1900.0, 1900.0, 1900.0, 1900.0, 1.0, 2.0),
        ],
    )

    result = read_amibroker_intraday_dat(file_path)

    assert result.iloc[0]["DateTime"] == pd.Timestamp("2026-09-04 09:15:30.123")
    assert result.iloc[0]["RawTime"] == 91530123


def test_read_intraday_filters_from_date_without_collapsing_ticks(tmp_path: Path) -> None:
    file_path = tmp_path / "VNINDEX.dat"
    _write_records(
        file_path,
        [
            (20260903, 145900, 1000.0, 1000.0, 1000.0, 1000.0, 10.0, 0.0),
            (20260904, 90000, 1001.0, 1001.0, 1001.0, 1001.0, 20.0, 0.0),
            (20260904, 90000, 1002.0, 1002.0, 1002.0, 1002.0, 30.0, 0.0),
        ],
    )

    result = read_amibroker_intraday_dat(file_path, from_date="2026-09-04")

    assert len(result) == 2
    assert result["TickSeq"].tolist() == [0, 1]
    assert {value.isoformat() for value in result["Date"]} == {"2026-09-04"}
