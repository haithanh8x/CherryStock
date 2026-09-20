from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


def file_hash(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 hash of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        while chunk := file_handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def files_are_different(source: Path, target: Path) -> bool:
    """Return True when target is missing or its content differs from source."""
    if not target.exists():
        return True
    if source.stat().st_size != target.stat().st_size:
        return True
    return file_hash(source) != file_hash(target)


def sync_folder(source_dir: Path, target_dir: Path) -> None:
    """Incrementally copy new or changed files from source_dir to target_dir."""
    source_dir = source_dir.resolve()
    target_dir = target_dir.resolve()

    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source folder does not exist: {source_dir}")

    if source_dir == target_dir:
        raise ValueError("Source and target folders must be different.")

    if source_dir in target_dir.parents:
        raise ValueError("Target folder must not be inside source folder.")

    target_dir.mkdir(parents=True, exist_ok=True)

    new_count = 0
    updated_count = 0
    skipped_count = 0

    for source_file in source_dir.rglob("*"):
        if not source_file.is_file():
            continue

        relative_path = source_file.relative_to(source_dir)
        target_file = target_dir / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)

        if not target_file.exists():
            shutil.copy2(source_file, target_file)
            print(f"[NEW]     {relative_path}")
            new_count += 1
        elif files_are_different(source_file, target_file):
            shutil.copy2(source_file, target_file)
            print(f"[UPDATED] {relative_path}")
            updated_count += 1
        else:
            skipped_count += 1

    print("\n===== SYNC SUMMARY =====")
    print(f"New     : {new_count}")
    print(f"Updated : {updated_count}")
    print(f"Skipped : {skipped_count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Incrementally sync new or changed files from folder A to folder B."
    )
    parser.add_argument("source", type=Path, help="Source folder (A)")
    parser.add_argument("target", type=Path, help="Target folder (B)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sync_folder(args.source, args.target)


if __name__ == "__main__":
    main()
