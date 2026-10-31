"""Publish current indicators, rolling 600-day history and calculated market breadth to R2.

History is stored as monthly Parquet partitions. The remote checkpoint is advanced
ONLY after every required partition and the chart-ready breadth JSON are published.
Reruns refresh the newest 10 trading dates to capture revised/provisional values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from src.cherrystock.config.settings import PROJECT_ROOT, settings
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory

BUCKET = "cherrystock"
SCHEMA = '"CherryMon"."main"'
CURRENT = f'{SCHEMA}."cal_indicator_current"'
HISTORY = f'{SCHEMA}."cal_indicator_history"'
EOD = f'{SCHEMA}."raw_stock_eod"'
CHECKPOINT = "cal_indicator_history/checkpoint.json"
CURRENT_KEY = "cal_indicator_current.parquet"
BREADTH_KEY = "market-breadth/v1/latest.json"
DAYS = 600


def _client():
    import boto3
    load_dotenv(PROJECT_ROOT / ".env")
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    if not all((account, key, secret)):
        raise RuntimeError("Missing R2 account/access key/secret in local .env")
    return boto3.client(
        "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=key, aws_secret_access_key=secret, region_name="auto",
    )


def _read_checkpoint(client):
    from botocore.exceptions import ClientError
    try:
        response = client.get_object(Bucket=BUCKET, Key=CHECKPOINT)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            return None
        raise
    body = json.loads(response["Body"].read())
    if body.get("schemaVersion") != 1 or not isinstance(body.get("months"), list):
        raise ValueError("Unknown R2 history checkpoint format; no uploads performed")
    return body


def _publish(client, file: Path, key: str, content_type: str):
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    staging = f"_staging/indicator-sync/{uuid4().hex}"
    metadata = {"sha256": digest}
    try:
        client.upload_file(str(file), BUCKET, staging, ExtraArgs={
            "ContentType": content_type, "Metadata": metadata})
        head = client.head_object(Bucket=BUCKET, Key=staging)
        if head["ContentLength"] != file.stat().st_size or head.get("Metadata", {}).get("sha256") != digest:
            raise RuntimeError(f"R2 staging verification failed: {key}")
        client.copy_object(Bucket=BUCKET, Key=key,
                           CopySource={"Bucket": BUCKET, "Key": staging},
                           MetadataDirective="COPY")
        published = client.head_object(Bucket=BUCKET, Key=key)
        if published["ContentLength"] != file.stat().st_size or published.get("Metadata", {}).get("sha256") != digest:
            raise RuntimeError(f"R2 publish verification failed: {key}")
    finally:
        client.delete_object(Bucket=BUCKET, Key=staging)
    return {"key": key, "bytes": file.stat().st_size, "sha256": digest}


def _export_parquet(con, sql: str, path: Path):
    escaped = str(path).replace("'", "''")
    con.execute(f"COPY ({sql}) TO '{escaped}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    if path.stat().st_size <= 0:
        raise RuntimeError(f"Empty parquet export: {path}")


def _breadth(con, window_start):
    """MA breadth using the indicator's OWN D/W/M timeframe, never resampling D.

    W/M observations occur only on observed period ends in the history export.
    Each denominator counts only eligible traded tickers with valid same-day
    MA and EOD close; missing MA readings never enter the denominator.
    """
    series = {}
    for tf in ("D", "W", "M"):
        records = con.execute(f"""
            WITH counts AS (
                SELECT h.Date AS Date, h.IndicatorName AS IndicatorName,
                       COUNT(*) AS eligible,
                       COUNT(*) FILTER (WHERE e.Close > h.Value) AS above
                FROM {HISTORY} AS h
                JOIN {EOD} AS e ON e.Ticker = h.Ticker AND e.Date = h.Date
                WHERE h.Timeframe = ?
                  AND h.IndicatorName IN ('MA20','MA50','MA100','MA200')
                  AND h.Date >= ?
                  AND h.Value IS NOT NULL AND isfinite(h.Value)
                  AND e.Close IS NOT NULL AND isfinite(e.Close)
                  AND e.Close > 0 AND e.Volume > 0
                GROUP BY h.Date, h.IndicatorName
            )
            SELECT Date,
                MAX(ROUND(100.0*above/NULLIF(eligible,0),2))
                    FILTER (WHERE IndicatorName='MA20') AS ma20,
                MAX(ROUND(100.0*above/NULLIF(eligible,0),2))
                    FILTER (WHERE IndicatorName='MA50') AS ma50,
                MAX(ROUND(100.0*above/NULLIF(eligible,0),2))
                    FILTER (WHERE IndicatorName='MA100') AS ma100,
                MAX(ROUND(100.0*above/NULLIF(eligible,0),2))
                    FILTER (WHERE IndicatorName='MA200') AS ma200,
                MAX(eligible) FILTER (WHERE IndicatorName='MA20') AS coverage
            FROM counts GROUP BY Date
            HAVING ma20 IS NOT NULL AND ma50 IS NOT NULL
               AND ma100 IS NOT NULL AND ma200 IS NOT NULL
            ORDER BY Date
        """, [tf, window_start]).fetchall()
        series[tf] = [
            {"date": str(r[0]), "ma20": float(r[1]), "ma50": float(r[2]),
             "ma100": float(r[3]), "ma200": float(r[4]), "coverage": int(r[5])}
            for r in records
        ]
    if not series["D"]:
        raise ValueError("No daily breadth rows from history + EOD")
    latest = series["D"][-1]["date"]
    moves = con.execute(f"""
        WITH eligible AS (
            SELECT DISTINCT Ticker FROM {HISTORY}
            WHERE Date=? AND Timeframe='D' AND IndicatorName='MA20'
        ), prices AS (
            SELECT e.Ticker, e.Date, e.Close, e.Volume,
                LAG(e.Close) OVER (PARTITION BY e.Ticker ORDER BY e.Date) AS previous
            FROM {EOD} e INNER JOIN eligible u ON u.Ticker=e.Ticker
            WHERE e.Date BETWEEN ? AND ?
        )
        SELECT
          COUNT(*) FILTER (WHERE Close > previous),
          COUNT(*) FILTER (WHERE Close < previous),
          COUNT(*) FILTER (WHERE Close = previous)
        FROM prices WHERE Date=? AND Close>0 AND previous>0 AND Volume>0
    """, [latest, datetime.strptime(latest, "%Y-%m-%d").date() - timedelta(days=30),
          latest, latest]).fetchone()
    return {
        "schemaVersion": 1,
        "source": "cal_indicator_history + raw_stock_eod",
        "asOf": latest, "windowDays": DAYS,
        "summary": {"advancers": int(moves[0]), "decliners": int(moves[1]), "unchanged": int(moves[2])},
        "method": "100 * count(Close > MA) / count(valid Close and MA), per native D/W/M timeframe, Volume>0",
        "breadth": series["D"],
        "timeframes": series,
    }


def sync(*, dry_run=False, db_path_override=None):
    db_path = Path(db_path_override).expanduser() if db_path_override else settings.local_db_path
    if not db_path.is_file():
        raise FileNotFoundError(str(db_path))
    client = None if dry_run else _client()
    checkpoint = None if dry_run else _read_checkpoint(client)

    factory = DuckDBConnectionFactory(db_path=db_path, duckdb_env="local")
    with factory.create_reader() as con:
        last, count = con.execute(f"SELECT MAX(Date), COUNT(*) FROM {HISTORY}").fetchone()
        if last is None or count == 0:
            raise RuntimeError("Indicator history is empty; run initial 600-bar load first")
        start = last - timedelta(days=DAYS - 1)
        total_current = con.execute(f"SELECT COUNT(*) FROM {CURRENT}").fetchone()[0]
        if total_current == 0:
            raise RuntimeError("cal_indicator_current empty; refusing R2 replacement")
        months = [row[0] for row in con.execute(f"""
            SELECT DISTINCT strftime(Date, '%Y-%m') AS month
            FROM {HISTORY} WHERE Date BETWEEN ? AND ?
            ORDER BY month
        """, [start, last]).fetchall()]
        latest_ten = con.execute(f"""
            SELECT MIN(Date) FROM (
                SELECT DISTINCT Date FROM {HISTORY} WHERE Date <= ?
                ORDER BY Date DESC LIMIT 10
            )
        """, [last]).fetchone()[0]
        if checkpoint:
            if checkpoint["lastDate"] > str(last):
                raise RuntimeError("R2 checkpoint is ahead of DuckDB history; abort")
            previous = set(checkpoint["months"])
            # Always rewrite newest 10 trading dates and the rolling oldest
            # partition, even if lastDate has not advanced since last sync.
            refresh_from = min(latest_ten, datetime.strptime(checkpoint["lastDate"], "%Y-%m-%d").date() + timedelta(days=1))
            selected = [m for m in months
                        if m not in previous or m >= refresh_from.strftime("%Y-%m")]
            if months:
                selected = sorted(set(selected) | {months[0], months[-1]})
        else:
            selected = months
        breadth = _breadth(con, start)
        result = {
            "bucket": BUCKET, "history_total_rows": count,
            "history_start": str(start), "history_last": str(last),
            "months_in_window": len(months), "months_to_sync": len(selected),
            "current_rows": total_current, "breadth_days": len(breadth["breadth"]),
            "breadth_as_of": breadth["asOf"], "dry_run": dry_run,
        }
        if dry_run:
            return result

        with tempfile.TemporaryDirectory(prefix="cherrystock-indicator-r2-") as tmp:
            root = Path(tmp)
            current_file = root / "current.parquet"
            _export_parquet(con, f"SELECT * FROM {CURRENT}", current_file)
            _publish(client, current_file, CURRENT_KEY, "application/octet-stream")
            print(f"[R2 INDICATOR] current uploaded: {total_current} rows", flush=True)

            for i, month in enumerate(selected, 1):
                file = root / "history.parquet"
                _export_parquet(con, f"""
                    SELECT * FROM {HISTORY}
                    WHERE Date BETWEEN DATE '{start}' AND DATE '{last}'
                      AND strftime(Date, '%Y-%m') = '{month}'
                """, file)
                _publish(client, file, f"cal_indicator_history/month={month}.parquet", "application/octet-stream")
                file.unlink()
                print(f"[R2 INDICATOR] history month {i}/{len(selected)}: {month}", flush=True)

            chart_file = root / "breadth.json"
            chart_file.write_text(json.dumps(breadth, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            _publish(client, chart_file, BREADTH_KEY, "application/json")
            next_checkpoint = {
                "schemaVersion": 1, "windowDays": DAYS,
                "windowStart": str(start), "lastDate": str(last),
                "months": months, "breadthAsOf": breadth["asOf"],
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }
            ck_file = root / "checkpoint.json"
            ck_file.write_text(json.dumps(next_checkpoint, indent=2), encoding="utf-8")
            _publish(client, ck_file, CHECKPOINT, "application/json")
            result["published_months"] = selected
            # Remove expired old partitions only after the new checkpoint commits.
            for month in set(checkpoint["months"] if checkpoint else []) - set(months):
                client.delete_object(Bucket=BUCKET, Key=f"cal_indicator_history/month={month}.parquet")
            return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--db-path", help="Consistent standalone DuckDB database path")
    args = parser.parse_args()
    print(json.dumps(sync(dry_run=args.dry_run, db_path_override=args.db_path),
                     ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
