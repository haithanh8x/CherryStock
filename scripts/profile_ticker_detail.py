"""Measure production ticker loader stages and optional Python call hotspots."""
from __future__ import annotations

import argparse
import cProfile
import csv
import math
import platform
import pstats
import statistics
import sys
from pathlib import Path

# Match the neighboring validate_smart_money_ui_snapshot.py src-layout bootstrap.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from webapp.ticker_detail_contract import normalize_ticker  # noqa: E402
from webapp.ticker_detail_data import load_ticker_details  # noqa: E402
from webapp.ticker_detail_trace import TickerTrace  # noqa: E402

OUTPUT = PROJECT_ROOT / "docs/reference/data/smart_money/ticker_detail_popup"


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summary_rows(events):
    groups = {}
    for event in events:
        groups.setdefault((event["ticker"], event["stage"]), []).append(event)
    result = []
    for (ticker, stage), rows in sorted(groups.items()):
        values = sorted(row["duration_ms"] for row in rows)
        result.append({
            "ticker": ticker, "stage": stage, "samples": len(rows),
            "errors": sum(row["status"] != "ok" for row in rows),
            "first_ms": rows[0]["duration_ms"],
            "median_ms": round(statistics.median(values), 3),
            "p95_ms": values[max(0, math.ceil(len(values) * 0.95) - 1)],
            "max_ms": max(values),
        })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", nargs="+", default=["MWG", "SHS", "ACV"])
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--profile", action="store_true", help="Adds cProfile overhead; compare separately with baseline.")
    args = parser.parse_args()
    if not 1 <= args.repeat <= 10 or not 1 <= len(args.tickers) <= 10:
        parser.error("Use 1–10 tickers and 1–10 repetitions.")
    try:
        tickers = list(dict.fromkeys(normalize_ticker(value) for value in args.tickers))
    except ValueError as exc:
        parser.error(str(exc))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    events, calls = [], []
    failed = False
    suffix = "profiled" if args.profile else "baseline"
    for ticker in tickers:
        for repetition in range(1, args.repeat + 1):
            trace = TickerTrace(ticker)
            profiler = cProfile.Profile() if args.profile else None
            if profiler:
                profiler.enable()
            try:
                with trace.span("cli.load"):
                    result = load_ticker_details(ticker, trace)
                failed |= bool(result["errors"])
                if result["errors"]:
                    print(f"{ticker} sample={repetition} incomplete panels={','.join(result['errors'])}")
            except Exception as exc:
                failed = True
                print(f"{ticker} sample={repetition} failed: {type(exc).__name__}")
            finally:
                if profiler:
                    profiler.disable()
                    stats = pstats.Stats(profiler)
                    top = sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)[:100]
                    for (filename, line, function), (primitive, total, own, cumulative, _callers) in top:
                        try:
                            safe_file = str(Path(filename).resolve().relative_to(PROJECT_ROOT))
                        except (ValueError, OSError):
                            safe_file = Path(filename).name  # no machine/user directory export
                        calls.append({
                            "request_id": trace.request_id, "ticker": ticker, "sample": repetition,
                            "file": safe_file, "line": line, "function": function, "calls": total,
                            "primitive_calls": primitive, "self_ms": round(own * 1000, 3),
                            "cumulative_ms": round(cumulative * 1000, 3),
                        })
                for event in trace.events:
                    events.append({**event, "sample": repetition, "profiled": bool(profiler),
                                   "python": platform.python_version()})
    write_csv(OUTPUT / f"stages_{suffix}.csv", events, [
        "utc", "request_id", "ticker", "sample", "stage", "status", "duration_ms",
        "elapsed_ms", "rows", "profiled", "python",
    ])
    summaries = summary_rows(events)
    write_csv(OUTPUT / f"summary_{suffix}.csv", summaries, [
        "ticker", "stage", "samples", "errors", "first_ms", "median_ms", "p95_ms", "max_ms",
    ])
    if calls:
        write_csv(OUTPUT / "python_hotspots.csv", calls, [
            "request_id", "ticker", "sample", "file", "line", "function",
            "calls", "primitive_calls", "self_ms", "cumulative_ms",
        ])
    for row in sorted(summaries, key=lambda item: item["median_ms"], reverse=True)[:20]:
        print(f"{row['ticker']:8} {row['stage']:48} median={row['median_ms']:10.3f} ms errors={row['errors']}")
    print(f"Evidence: {OUTPUT.relative_to(PROJECT_ROOT)}; partial/error={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
