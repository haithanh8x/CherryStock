"""Publish a DuckDB view as Parquet to Cloudflare R2 (S3-compatible)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

import duckdb
from dotenv import load_dotenv

from src.cherrystock.config.settings import PROJECT_ROOT, settings

VIEW = "vw_Ticker_Active"
BUCKET = "cherrystock"
KEY = f"{VIEW}.parquet"
SOURCE = f'"CherryMon"."main"."{VIEW}"'


def sync(*, dry_run: bool = False, db_path_override: str | None = None) -> dict[str, object]:
    load_dotenv(PROJECT_ROOT / ".env")
    db_path = Path(db_path_override).expanduser() if db_path_override else settings.local_db_path
    if not db_path.is_file():
        raise FileNotFoundError(f"DuckDB database not found: {db_path}")

    with tempfile.TemporaryDirectory(prefix="cherrystock-r2-") as tmp:
        output = Path(tmp) / KEY
        try:
            con = duckdb.connect(str(db_path), read_only=True)
        except (duckdb.Error, OSError) as exc:
            wal_path = Path(str(db_path) + ".wal")
            raise RuntimeError(
                f"Cannot open DuckDB read-only: {db_path}. "
                f"WAL present: {wal_path.exists()}. "
                "Close active DuckDB writers and allow a clean checkpoint/close; "
                "then retry. If this persists, have the owning process create "
                "a consistent DuckDB snapshot using EXPORT DATABASE, and pass "
                "--db-path to a properly restored standalone database. "
                "Do NOT delete/copy the .wal or force a checkpoint while writers are active. "
                f"Original error: {exc}"
            ) from exc
        with con:
            count = con.execute(f"SELECT COUNT(*) FROM {SOURCE}").fetchone()[0]
            if count <= 0:
                raise ValueError(f"Refusing to publish empty view: {SOURCE}")
            output_sql = str(output).replace("'", "''")
            con.execute(f"COPY (SELECT * FROM {SOURCE}) TO '{output_sql}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        result = {
            "source": SOURCE, "bucket": BUCKET, "key": KEY,
            "rows": count, "bytes": output.stat().st_size, "sha256": digest,
            "dry_run": dry_run,
        }
        if dry_run:
            return result

        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("Install boto3: pip install boto3") from exc

        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
        access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
        secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
        if not all((account_id, access_key, secret_key)):
            raise RuntimeError(
                "Set CLOUDFLARE_ACCOUNT_ID, R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY in .env"
            )
        client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        temp_key = f"_staging/{VIEW}/{uuid4().hex}.parquet"
        try:
            client.upload_file(
                str(output), BUCKET, temp_key,
                ExtraArgs={"Metadata": {"sha256": digest, "source-view": VIEW}},
            )
            head = client.head_object(Bucket=BUCKET, Key=temp_key)
            if head["ContentLength"] != output.stat().st_size or head.get("Metadata", {}).get("sha256") != digest:
                raise RuntimeError("Staging upload verification failed; published object untouched")
            # Copy the fully uploaded staging object to the stable name.
            client.copy_object(
                Bucket=BUCKET, Key=KEY,
                CopySource={"Bucket": BUCKET, "Key": temp_key},
                MetadataDirective="COPY",
            )
            published = client.head_object(Bucket=BUCKET, Key=KEY)
            if published["ContentLength"] != output.stat().st_size or published.get("Metadata", {}).get("sha256") != digest:
                raise RuntimeError("Published object verification failed")
        finally:
            client.delete_object(Bucket=BUCKET, Key=temp_key)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync vw_Ticker_Active to R2 cherrystock")
    parser.add_argument("--dry-run", action="store_true", help="Export and validate without uploading")
    parser.add_argument("--db-path", help="Path to a standalone consistent DuckDB database snapshot")
    args = parser.parse_args()
    print(json.dumps(sync(dry_run=args.dry_run, db_path_override=args.db_path), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
