from __future__ import annotations

import os
import shutil
import sqlite3

from core.logger import logger
from paths import get_data_dir


def is_database_locked(db_path: str) -> bool:
    """
    Check if an SQLite database is currently held open or locked by another process.
    """
    if not os.path.isfile(db_path):
        return False
    # 1. Check SQLite transaction lock
    try:
        conn = sqlite3.connect(db_path, timeout=1.0)
        try:
            conn.execute("BEGIN EXCLUSIVE;")
            conn.execute("COMMIT;")
        finally:
            conn.close()
            del conn
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return True
    finally:
        import gc
        gc.collect()

    # 2. Check OS-level file handle locks on db and sidecars
    files_to_check = [db_path]
    for ext in ["-wal", "-shm"]:
        sidecar = db_path + ext
        if os.path.isfile(sidecar):
            files_to_check.append(sidecar)

    for fpath in files_to_check:
        try:
            # On Windows, os.rename to itself requires FILE_SHARE_DELETE; fails if file is open
            os.rename(fpath, fpath)
        except (PermissionError, OSError):
            return True

    return False


def migrate_legacy_outbox(data_dir: str | None = None) -> bool:
    """
    Explicit startup migration helper for Phase 8 -> Phase 9 outbox relocation.

    Old location: <data_dir>/outbox/outbox.db (and -wal, -shm)
    New location: <data_dir>/data/outbox/outbox.db (and -wal, -shm)

    Rules:
    1. If old outbox does not exist, return True (fresh installation or already migrated).
    2. If both old and new outboxes exist, do NOT overwrite or merge.
       Log an actionable error and raise RuntimeError to fail safely.
    3. If old exists and new does not:
       a. Verify old database is not in active use / locked.
       b. Checkpoint WAL frames cleanly if possible.
       c. Atomically move outbox.db and sidecar files (-wal, -shm) to new folder.
       d. Clean up empty legacy outbox folder if empty.
    4. Idempotent and safe against concurrent runs.
    """
    base_dir = data_dir or get_data_dir()
    old_folder = os.path.join(base_dir, "outbox")
    old_db = os.path.join(old_folder, "outbox.db")

    new_folder = os.path.join(base_dir, "data", "outbox")
    new_db = os.path.join(new_folder, "outbox.db")

    # 1. If old DB does not exist, nothing to migrate
    if not os.path.isfile(old_db):
        return True

    # 2. Both old and new exist: CONFLICT condition
    if os.path.isfile(new_db):
        err_msg = (
            f"Outbox migration conflict: Both legacy outbox ({old_db}) "
            f"and new outbox ({new_db}) exist. Refusing to overwrite or merge. "
            f"Administrator action required to inspect and consolidate outbox records."
        )
        logger.critical(err_msg)
        raise RuntimeError(err_msg)

    # 3. Verify old database is not actively open / locked
    if is_database_locked(old_db):
        err_msg = (
            f"Cannot migrate outbox: legacy database '{old_db}' is currently in use "
            f"or locked by another process. Migration aborted to prevent data corruption."
        )
        logger.critical(err_msg)
        raise RuntimeError(err_msg)

    logger.info(f"Initiating legacy outbox migration from '{old_db}' to '{new_db}'...")

    # Best-effort WAL checkpoint before moving files
    try:
        conn = sqlite3.connect(old_db, timeout=5.0)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        finally:
            conn.close()
            del conn
    except Exception as exc:
        logger.warning(f"Notice: WAL checkpoint prior to outbox migration encountered: {exc}")
    finally:
        import gc
        gc.collect()

    # Ensure destination directory exists
    os.makedirs(new_folder, exist_ok=True)

    # Move sidecar files first, then main db file
    sidecars = ["-wal", "-shm"]
    moved_sidecars: list[tuple[str, str]] = []
    try:
        for ext in sidecars:
            old_sidecar = old_db + ext
            new_sidecar = new_db + ext
            if os.path.isfile(old_sidecar):
                shutil.move(old_sidecar, new_sidecar)
                moved_sidecars.append((new_sidecar, old_sidecar))

        shutil.move(old_db, new_db)
        logger.info(f"Successfully migrated outbox database to '{new_db}'.")

        # Best-effort cleanup of old outbox directory if now empty
        try:
            if os.path.isdir(old_folder) and not os.listdir(old_folder):
                os.rmdir(old_folder)
                logger.debug(f"Removed empty legacy outbox folder '{old_folder}'.")
        except OSError:
            pass

        return True
    except Exception as exc:
        # If moving failed midway, attempt roll back of moved sidecars
        logger.critical(f"Critical failure during outbox file migration: {exc}")
        for new_f, old_f in moved_sidecars:
            try:
                if os.path.isfile(new_f) and not os.path.isfile(old_f):
                    shutil.move(new_f, old_f)
            except Exception:
                pass
        raise RuntimeError(f"Outbox migration failed: {exc}") from exc
