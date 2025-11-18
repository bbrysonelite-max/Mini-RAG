"""
Utilities for creating safety backups of the chunks JSONL file.

We snapshot the current chunks file before any destructive or mutating write
operation so recovery is always possible if a write fails partway through.
"""

import datetime
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, List


class ChunkBackupError(IOError):
    """Raised when backup creation fails."""


def _resolve_backup_directory(chunks_path: Path) -> Path:
    """
    Determine where backups should live.

    We prefer a top-level `backups/` directory when the chunks file sits in
    the default `out/` folder; otherwise we colocate `backups/` alongside the
    chunks file. Using `.resolve()` keeps behavior predictable.
    """
    resolved = chunks_path.resolve()
    if resolved.parent.name.lower() == "out":
        # Default layout: project_root/out/chunks.jsonl → project_root/backups/
        base_dir = resolved.parent.parent
    else:
        base_dir = resolved.parent

    if not str(base_dir):
        base_dir = Path(".").resolve()

    return base_dir / "backups"


def create_chunk_backup(chunks_path: str) -> Optional[str]:
    """
    Create a timestamped backup copy of the chunks JSONL file.

    Args:
        chunks_path: Path to the live chunks file.

    Returns:
        The absolute path to the backup file when one is created.

    Raises:
        ChunkBackupError: If we fail to copy the file or update the latest pointer.
    """
    source = Path(chunks_path).expanduser()
    if not source.exists():
        # Nothing to backup yet; safe to skip.
        return None

    backup_dir = _resolve_backup_directory(source)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    backup_name = f"{source.stem}-{timestamp}{source.suffix or '.jsonl'}"
    backup_path = backup_dir / backup_name
    latest_path = backup_dir / "latest.jsonl"

    try:
        os.makedirs(backup_dir, exist_ok=True)
        # Copy current chunks file to a timestamped backup.
        shutil.copy2(source, backup_path)
        # Maintain an easy-to-find latest snapshot for quick restores.
        shutil.copy2(backup_path, latest_path)
    except OSError as err:
        raise ChunkBackupError(f"Failed to create backup for {source}: {err}") from err

    return str(backup_path)


def restore_chunk_backup(
    chunks_path: str,
    backup_path: Optional[str] = None,
    *,
    skip_prebackup: bool = False,
) -> Tuple[str, str]:
    """
    Restore the chunks file from the latest (or specified) backup.

    Args:
        chunks_path: Target chunks file to restore.
        backup_path: Optional explicit backup file; defaults to `backups/latest.jsonl`.
        skip_prebackup: Internal/testing flag to bypass snapshotting the current file.

    Returns:
        Tuple of (restored_from, pre_backup_path).
    """
    target = Path(chunks_path).expanduser()
    backup_dir = _resolve_backup_directory(target)
    if backup_path:
        candidate_path = Path(backup_path).expanduser()
    else:
        pattern_suffix = target.suffix or ".jsonl"
        pattern = f"{target.stem}-*{pattern_suffix}"
        timestamp_backups: List[Path] = sorted(
            p for p in backup_dir.glob(pattern) if p.is_file()
        )
        if not timestamp_backups:
            raise ChunkBackupError(f"No timestamped backups available in {backup_dir}")
        candidate_path = timestamp_backups[-1]

    if not candidate_path.exists():
        raise ChunkBackupError(f"Backup file not found: {candidate_path}")
    if not candidate_path.is_file():
        raise ChunkBackupError(f"Backup path is not a file: {candidate_path}")

    # Optionally snapshot current state before overwriting.
    pre_backup_path = ""
    if not skip_prebackup:
        pre_backup_path = create_chunk_backup(chunks_path) or ""

    try:
        os.makedirs(target.parent, exist_ok=True)
        shutil.copy2(candidate_path, target)
        latest_path = backup_dir / "latest.jsonl"
        shutil.copy2(candidate_path, latest_path)
    except OSError as err:
        raise ChunkBackupError(f"Failed to restore {chunks_path} from {candidate_path}: {err}") from err

    return str(candidate_path), pre_backup_path

