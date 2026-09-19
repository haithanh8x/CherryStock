from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BASELINE_COMMIT = "0d7ff1b27862c7415affc8ca1fa9c65d304ba92e"

# Files that existed before Price Movement implementation and must be restored
# exactly to the pre-implementation baseline.
RESTORE_FROM_BASELINE = [
    "docs/backlog/requirements/REQ-0027-price-movement-characterization.md",
    "run.py",
    "src/cherrystock/application/services/sync_write_pipeline.py",
    "src/cherrystock/infrastructure/database/repositories/__init__.py",
    "src/cherrystock/infrastructure/database/unit_of_work.py",
]

# Implementation artifacts introduced after BASELINE_COMMIT.
REMOVE_TRACKED_FILES = [
    "docs/development/implementation-notes/REQ-0027-price-movement-character-v1.md",
    "docs/runbook/Price_Movement_Character_V1.md",
    "docs/runbook/Price_Movement_Character_V1_Validation_After_PIT_Fix.md",
    "scripts/diag_price_movement_nan.py",
    "scripts/diag_price_movement_no_lookahead.py",
    "scripts/diag_price_movement_zero_price.py",
    "scripts/initload/init_reload_price_movement_character.py",
    "scripts/inspect_price_movement.py",
    "scripts/run_price_movement.py",
    "scripts/validate_price_movement_character.py",
    "src/DuckDB/sql/price_movement_character_v1_profile_view.sql",
    "src/DuckDB/sql/price_movement_character_v1_schema.sql",
    "src/calcEngine/priceMovementCharacter.py",
    "src/cherrystock/domain/__init__.py",
    "src/cherrystock/domain/analytics/__init__.py",
    "src/cherrystock/domain/analytics/price_movement/__init__.py",
    "src/cherrystock/domain/analytics/price_movement/engine.py",
    "src/cherrystock/domain/analytics/price_movement/models.py",
    "src/cherrystock/domain/analytics/price_movement/runtime.py",
    "src/cherrystock/domain/analytics/price_movement/source_quality.py",
    "src/cherrystock/infrastructure/database/price_movement_validation.py",
    "src/cherrystock/infrastructure/database/repositories/price_movement_repository.py",
    "tests/test_price_movement_character.py",
    "tests/test_price_movement_pipeline_order.py",
    "tests/test_price_movement_profile_contract.py",
    "tests/test_price_movement_runtime.py",
]

# Local profiler artifacts may be untracked and therefore are not covered by git rm.
OPTIONAL_LOCAL_ARTIFACTS = [
    "scripts/prof_price_movement_timing.py",
    "price_movement_timing_full.txt",
    "scripts/price_movement_timing_full.txt",
]

DROP_VIEWS = [
    'vw_Ticker_Movement_Profile',
    'vw_Ticker_Movement_D',
    'vw_Ticker_Movement_Swings',
]

DROP_TABLES = [
    'cal_price_movement_daily',
    'cal_price_movement_swing',
    'dim_price_movement_config',
    'dim_price_movement_model',
]


def run_git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=check,
        text=True,
        capture_output=True,
    )


def tracked(repo_root: Path, path: str) -> bool:
    result = run_git(repo_root, "ls-files", "--error-unmatch", "--", path, check=False)
    return result.returncode == 0


def dirty_paths(repo_root: Path) -> list[str]:
    result = run_git(repo_root, "status", "--porcelain")
    paths: list[str] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line.strip():
            continue
        value = raw_line[3:].strip()
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.append(value.replace("\\", "/"))
    return paths


def is_known_local_artifact(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized in OPTIONAL_LOCAL_ARTIFACTS:
        return True
    return normalized.startswith("price_movement_timing_") and normalized.endswith(".txt")


def verify_preflight(repo_root: Path, allow_dirty: bool) -> None:
    top = Path(run_git(repo_root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if top != repo_root.resolve():
        raise RuntimeError(f"Expected repo root {repo_root}, got {top}")

    baseline = run_git(
        repo_root,
        "cat-file",
        "-e",
        f"{BASELINE_COMMIT}^{{commit}}",
        check=False,
    )
    if baseline.returncode != 0:
        raise RuntimeError(
            f"Baseline commit {BASELINE_COMMIT} is not available locally. Run git fetch origin first."
        )

    dirty = dirty_paths(repo_root)
    unexpected = [path for path in dirty if not is_known_local_artifact(path)]
    if unexpected and not allow_dirty:
        joined = "\n  - ".join(unexpected)
        raise RuntimeError(
            "Unexpected local changes detected. Commit/stash them first, or rerun with --allow-dirty:\n"
            f"  - {joined}"
        )


def print_plan(repo_root: Path) -> None:
    print("=== Price Movement V1 rollback plan ===")
    print(f"Repository: {repo_root}")
    print(f"Baseline:   {BASELINE_COMMIT}")
    print()
    print("Database objects to DROP:")
    for name in DROP_VIEWS:
        print(f"  VIEW  CherryMon.main.{name}")
    for name in DROP_TABLES:
        print(f"  TABLE CherryMon.main.{name}")
    print("  AUDIT rows where pipeline = 'Price Movement Character' (when audit table exists)")
    print()
    print("Files to restore from baseline:")
    for path in RESTORE_FROM_BASELINE:
        print(f"  RESTORE {path}")
    print()
    print("Tracked implementation files to remove:")
    for path in REMOVE_TRACKED_FILES:
        if tracked(repo_root, path):
            print(f"  REMOVE  {path}")
    print()
    print("Optional local profiler artifacts to remove if present:")
    for path in OPTIONAL_LOCAL_ARTIFACTS:
        if (repo_root / path).exists():
            print(f"  REMOVE  {path}")


def drop_database_objects(repo_root: Path) -> None:
    sys.path.insert(0, str(repo_root / "src"))

    from cherrystock.config.settings import settings
    from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    connection = factory.create_writer()
    try:
        connection.execute("BEGIN")

        # Remove audit evidence produced by the retired implementation, if the
        # shared audit table exists. Do not drop the shared audit table itself.
        audit_exists = connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'main'
              AND table_name = 'sys_data_quality_audit'
            """
        ).fetchone()[0]
        if audit_exists:
            columns = {
                str(row[0]).lower()
                for row in connection.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'main'
                      AND table_name = 'sys_data_quality_audit'
                    """
                ).fetchall()
            }
            if "pipeline" in columns:
                connection.execute(
                    '''
                    DELETE FROM "CherryMon"."main"."sys_data_quality_audit"
                    WHERE pipeline = 'Price Movement Character'
                    '''
                )

        for view_name in DROP_VIEWS:
            connection.execute(
                f'DROP VIEW IF EXISTS "CherryMon"."main"."{view_name}"'
            )

        for table_name in DROP_TABLES:
            connection.execute(
                f'DROP TABLE IF EXISTS "CherryMon"."main"."{table_name}"'
            )

        connection.execute("COMMIT")
        print("[DB] Price Movement views/tables dropped and audit rows cleaned.")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def rollback_source(repo_root: Path) -> None:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_branch = f"backup/pre-price-movement-rollback-{timestamp}"
    run_git(repo_root, "branch", backup_branch, "HEAD")
    print(f"[git] Backup branch created: {backup_branch}")

    # Restore only shared files that were modified for Price Movement.
    for path in RESTORE_FROM_BASELINE:
        run_git(
            repo_root,
            "restore",
            "--source",
            BASELINE_COMMIT,
            "--staged",
            "--worktree",
            "--",
            path,
        )
        print(f"[git] restored: {path}")

    # Remove files that did not exist at the baseline.
    for path in REMOVE_TRACKED_FILES:
        if tracked(repo_root, path):
            run_git(repo_root, "rm", "-f", "--", path)
            print(f"[git] removed:  {path}")

    # Remove known local-only profiling artifacts.
    for path in OPTIONAL_LOCAL_ARTIFACTS:
        target = repo_root / path
        if target.exists() and not tracked(repo_root, path):
            target.unlink()
            print(f"[local] removed: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rollback Price Movement Character V1 to the repository state immediately "
            "before implementation. Dry-run by default."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually drop DB objects and modify the working tree.",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Rollback source only; do not modify DuckDB.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow unrelated local changes. Use only when you have reviewed them.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    verify_preflight(repo_root, allow_dirty=args.allow_dirty)
    print_plan(repo_root)

    if not args.execute:
        print()
        print("DRY RUN ONLY — no changes were made.")
        print("Run again with --execute after reviewing the plan.")
        return 0

    print()
    print("=== Executing rollback ===")
    if not args.skip_db:
        drop_database_objects(repo_root)
    else:
        print("[DB] skipped by --skip-db")

    rollback_source(repo_root)

    print()
    print("=== Rollback staged in working tree ===")
    status = run_git(repo_root, "status", "--short")
    print(status.stdout.rstrip() or "(clean)")
    print()
    print("Review the diff before committing:")
    print("  git diff --cached")
    print("  git status")
    print()
    print("Recommended verification:")
    print("  python run.py")
    print()
    print("The requirement/architecture material that already existed at the baseline is preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
