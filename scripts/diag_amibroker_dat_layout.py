from __future__ import annotations

import argparse
import math
import os
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable


DEFAULT_AMIBROKER_ROOT = Path("C:/Program1/AmiBroker/Data_FireAnt/AmiBroker")


@dataclass
class DecodedRecord:
    dt: datetime | None
    close: float
    open: float
    high: float
    low: float
    volume: float
    open_interest: float
    aux1: float | None = None
    aux2: float | None = None
    raw_date: int | None = None
    raw_time: int | None = None


@dataclass
class LayoutProbe:
    name: str
    record_size: int
    decoder: Callable[[bytes], DecodedRecord | None]


def decode_current_32(chunk: bytes) -> DecodedRecord | None:
    """
    Decode the layout currently assumed by src/CrawlStock/readAmi.py:

        int32 Date(YYYYMMDD)
        int32 Time
        float Open
        float High
        float Low
        float Close
        float Volume
        float OpenInt
    """
    if len(chunk) != 32:
        return None

    raw_date, raw_time, open_, high, low, close, volume, open_interest = struct.unpack(
        "<iiffffff", chunk
    )

    if not 19000101 <= raw_date <= 21001231:
        return None

    try:
        dt = datetime.strptime(str(raw_date), "%Y%m%d")
    except ValueError:
        return None

    return DecodedRecord(
        dt=dt,
        close=close,
        open=open_,
        high=high,
        low=low,
        volume=volume,
        open_interest=open_interest,
        raw_date=raw_date,
        raw_time=raw_time,
    )


def decode_amidate(value: int) -> datetime | None:
    """
    Decode AmiBroker ADK 64-bit AmiDate/PackedDate.

    Bit layout from current AmiBroker ADK:
      bit 0       IsFuturePad
      bits 1..5   Reserved
      bits 6..15  MicroSec
      bits 16..25 MilliSec
      bits 26..31 Second
      bits 32..37 Minute
      bits 38..42 Hour
      bits 43..47 Day
      bits 48..51 Month
      bits 52..63 Year

    EOD records use Hour=31 and Minute=63.
    """
    micro = (value >> 6) & 0x3FF
    milli = (value >> 16) & 0x3FF
    second = (value >> 26) & 0x3F
    minute = (value >> 32) & 0x3F
    hour = (value >> 38) & 0x1F
    day = (value >> 43) & 0x1F
    month = (value >> 48) & 0x0F
    year = (value >> 52) & 0x0FFF

    if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
        return None

    # AmiBroker EOD marker.
    if hour == 31 and minute == 63:
        hour = minute = second = milli = micro = 0
    elif not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        return None

    try:
        return datetime(
            year,
            month,
            day,
            hour,
            minute,
            second,
            milli * 1000 + micro,
        )
    except ValueError:
        return None


def decode_adk_40(chunk: bytes) -> DecodedRecord | None:
    """
    Probe the 40-byte AmiBroker ADK Quotation layout:

        AmiDate DateTime (uint64)
        float Price        # Close
        float Open
        float High
        float Low
        float Volume
        float OpenInterest
        float AuxData1
        float AuxData2

    NOTE: ADK documents the in-memory/plugin quotation structure. This probe
    intentionally verifies whether the supplied .dat file follows that same
    raw layout; it does not assume that every AmiBroker database file does.
    """
    if len(chunk) != 40:
        return None

    (
        raw_datetime,
        close,
        open_,
        high,
        low,
        volume,
        open_interest,
        aux1,
        aux2,
    ) = struct.unpack("<Qffffffff", chunk)

    dt = decode_amidate(raw_datetime)
    if dt is None:
        return None

    return DecodedRecord(
        dt=dt,
        close=close,
        open=open_,
        high=high,
        low=low,
        volume=volume,
        open_interest=open_interest,
        aux1=aux1,
        aux2=aux2,
    )


LAYOUTS = (
    LayoutProbe("current_readAmi_32", 32, decode_current_32),
    LayoutProbe("amibroker_adk_40", 40, decode_adk_40),
)


def is_finite_number(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def record_sanity_score(record: DecodedRecord | None) -> float:
    if record is None or record.dt is None:
        return 0.0

    prices = [record.open, record.high, record.low, record.close]
    if not all(is_finite_number(x) for x in prices):
        return 0.0

    score = 0.35  # valid date/datetime

    if all(-1e8 < x < 1e9 for x in prices):
        score += 0.15

    if record.high >= max(record.open, record.close, record.low):
        score += 0.15

    if record.low <= min(record.open, record.close, record.high):
        score += 0.15

    if is_finite_number(record.volume) and 0 <= record.volume < 1e15:
        score += 0.10

    if is_finite_number(record.open_interest) and abs(record.open_interest) < 1e15:
        score += 0.10

    return score


def decode_records(
    data: bytes,
    layout: LayoutProbe,
    offset: int,
    max_records: int,
) -> list[DecodedRecord]:
    records: list[DecodedRecord] = []
    pos = offset
    end = len(data)

    while pos + layout.record_size <= end and len(records) < max_records:
        chunk = data[pos : pos + layout.record_size]
        record = layout.decoder(chunk)
        if record is not None:
            records.append(record)
        pos += layout.record_size

    return records


def alignment_quality(
    data: bytes,
    layout: LayoutProbe,
    offset: int,
    max_records: int,
) -> tuple[float, int]:
    pos = offset
    end = len(data)
    scores: list[float] = []

    while pos + layout.record_size <= end and len(scores) < max_records:
        chunk = data[pos : pos + layout.record_size]
        scores.append(record_sanity_score(layout.decoder(chunk)))
        pos += layout.record_size

    if not scores:
        return 0.0, 0

    valid = sum(1 for x in scores if x >= 0.70)
    return valid / len(scores), len(scores)


def find_best_alignment(
    data: bytes,
    layout: LayoutProbe,
    max_records: int,
) -> tuple[int, float, int]:
    best_offset = 0
    best_quality = -1.0
    best_count = 0

    # Scan one record-width worth of possible leading/header offsets.
    for offset in range(layout.record_size):
        quality, count = alignment_quality(data, layout, offset, max_records)
        if quality > best_quality:
            best_offset = offset
            best_quality = quality
            best_count = count

    return best_offset, best_quality, best_count


def tail_records(
    data: bytes,
    layout: LayoutProbe,
    offset: int,
    count: int,
) -> list[DecodedRecord]:
    usable = len(data) - offset
    total = usable // layout.record_size
    start_index = max(0, total - count)
    records: list[DecodedRecord] = []

    for index in range(start_index, total):
        pos = offset + index * layout.record_size
        record = layout.decoder(data[pos : pos + layout.record_size])
        if record is not None:
            records.append(record)

    return records


def relative_error(value: float, target: float) -> float | None:
    if not is_finite_number(value) or not is_finite_number(target):
        return None
    scale = max(abs(target), 1e-9)
    return abs(value - target) / scale


def reference_similarity(
    records: Iterable[DecodedRecord],
) -> dict[str, tuple[int, int, float | None]]:
    """
    Compare OI/Aux1/Aux2 with previous Close.

    For ordinary HOSE/HNX sessions, previous Close is often the reference-price
    anchor, so a very high match rate is useful evidence. It is NOT proof because
    corporate actions, first trading days, UPCoM rules, and source conventions can
    legitimately differ.
    """
    rows = list(records)
    fields = ("open_interest", "aux1", "aux2")
    result: dict[str, tuple[int, int, float | None]] = {}

    for field in fields:
        compared = 0
        matched = 0
        errors: list[float] = []

        for prev, current in zip(rows, rows[1:]):
            if prev.dt is None or current.dt is None:
                continue
            if prev.dt.date() >= current.dt.date():
                continue

            value = getattr(current, field)
            if value is None:
                continue

            err = relative_error(float(value), float(prev.close))
            if err is None:
                continue

            compared += 1
            errors.append(err)
            if err <= 0.002:  # within 0.2%
                matched += 1

        mean_error = (sum(errors) / len(errors)) if errors else None
        result[field] = (matched, compared, mean_error)

    return result


def fmt(value: float | None) -> str:
    if value is None:
        return "-"
    if not math.isfinite(value):
        return str(value)
    return f"{value:,.6g}"


def print_records(records: list[DecodedRecord], max_rows: int) -> None:
    print(
        "DateTime                  Close        Open        High         Low"
        "       Volume         OI       Aux1       Aux2"
    )
    print("-" * 112)
    for record in records[-max_rows:]:
        dt_text = record.dt.isoformat(sep=" ") if record.dt else "-"
        print(
            f"{dt_text:<24}"
            f"{fmt(record.close):>12}"
            f"{fmt(record.open):>12}"
            f"{fmt(record.high):>12}"
            f"{fmt(record.low):>12}"
            f"{fmt(record.volume):>13}"
            f"{fmt(record.open_interest):>11}"
            f"{fmt(record.aux1):>11}"
            f"{fmt(record.aux2):>11}"
        )


def resolve_file(args: argparse.Namespace) -> Path:
    if args.file:
        return Path(args.file).expanduser()

    source = args.source.lower()
    if source == "eod":
        root = Path(
            os.getenv(
                "AMIBROKER_EOD_PATH",
                str(DEFAULT_AMIBROKER_ROOT / "EOD"),
            )
        )
    else:
        root = Path(
            os.getenv(
                "AMIBROKER_INTRADAY_PATH",
                str(DEFAULT_AMIBROKER_ROOT / "Intraday"),
            )
        )

    return root / "stock" / f"{args.ticker.upper()}.dat"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe CherryStock/FireAnt AmiBroker .dat record layout and check "
            "whether OpenInterest/Aux1/Aux2 behave like ReferencePrice."
        )
    )
    parser.add_argument("--file", help="Explicit .dat file path.")
    parser.add_argument("--ticker", default="FPT", help="Ticker when --file is omitted.")
    parser.add_argument(
        "--source",
        choices=("eod", "intraday"),
        default="eod",
        help="Default AmiBroker source tree when --file is omitted.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=20,
        help="Number of recent decoded rows to display.",
    )
    parser.add_argument(
        "--probe-records",
        type=int,
        default=500,
        help="Maximum records used for alignment scoring.",
    )
    args = parser.parse_args()

    file_path = resolve_file(args)
    print(f"File: {file_path}")

    if not file_path.exists():
        print("ERROR: file does not exist.")
        return 2

    data = file_path.read_bytes()
    print(f"File size: {len(data):,} bytes")

    for size in (32, 40, 48):
        print(
            f"size % {size:>2} = {len(data) % size:>2} "
            f"(exact multiple: {len(data) % size == 0})"
        )

    print()
    candidates: list[tuple[LayoutProbe, int, float, int]] = []

    for layout in LAYOUTS:
        offset, quality, checked = find_best_alignment(
            data,
            layout,
            max_records=max(1, args.probe_records),
        )
        candidates.append((layout, offset, quality, checked))
        print(
            f"[{layout.name}] size={layout.record_size} "
            f"best_offset={offset} valid_ratio={quality:.1%} checked={checked}"
        )

    candidates.sort(key=lambda x: x[2], reverse=True)

    print("\n=== Best candidate(s) ===")
    for layout, offset, quality, _ in candidates:
        if quality < 0.50:
            continue

        print(
            f"\n--- {layout.name}: record_size={layout.record_size}, "
            f"offset={offset}, valid_ratio={quality:.1%} ---"
        )

        # Use all available records for recent field-to-prev-close comparison,
        # capped to keep this diagnostic lightweight on large intraday files.
        usable = len(data) - offset
        total = usable // layout.record_size
        comparison_start = max(0, total - 5000)
        recent: list[DecodedRecord] = []
        for index in range(comparison_start, total):
            pos = offset + index * layout.record_size
            record = layout.decoder(data[pos : pos + layout.record_size])
            if record is not None:
                recent.append(record)

        print_records(recent, max_rows=max(1, args.rows))

        similarity = reference_similarity(recent)
        print("\nSimilarity to previous Close (heuristic only):")
        for field, (matched, compared, mean_error) in similarity.items():
            if compared == 0:
                print(f"  {field:>13}: no comparable observations")
                continue

            rate = matched / compared
            mean_text = f"{mean_error:.3%}" if mean_error is not None else "-"
            marker = ""
            if rate >= 0.80:
                marker = "  <-- strong ReferencePrice candidate"
            elif rate >= 0.60:
                marker = "  <-- possible candidate"

            print(
                f"  {field:>13}: {matched}/{compared} within 0.2% "
                f"({rate:.1%}), mean relative error={mean_text}{marker}"
            )

        if layout.name == "amibroker_adk_40":
            print(
                "\nADK-40 field order used here: "
                "DateTime, Close(Price), Open, High, Low, Volume, "
                "OpenInterest, Aux1, Aux2."
            )

    if candidates[0][2] < 0.50:
        print(
            "\nNo candidate achieved >=50% sane records. The file may contain "
            "a header/index, another proprietary layout, compression, or a record "
            "format different from both probes."
        )
        return 1

    print(
        "\nInterpretation: a high Aux1/Aux2 match to previous Close is useful "
        "evidence, not proof. Verify several ordinary trading dates against "
        "FireAnt/AmiBroker Quote Editor before assigning ReferencePrice semantics."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
