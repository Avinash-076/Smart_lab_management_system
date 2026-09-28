from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from config import (
    DIAGNOSTIC_MAX_FILES,
    OUTPUT_FOLDER,
)
from core.logger import logger


def clean_legacy_diagnostic_files(
    directory: str = OUTPUT_FOLDER,
    keep_filename: str = "client_data.json",
    max_files: int = DIAGNOSTIC_MAX_FILES,
) -> None:
    """
    Remove obsolete or historical timestamped diagnostic files from previous versions.
    Ensures the diagnostic directory adheres to the ONE current snapshot policy.
    """
    try:
        if not os.path.isdir(directory):
            return

        entries = os.listdir(directory)
        legacy_files = [
            f for f in entries
            if f != keep_filename and f.startswith("client_data") and f.endswith(".json")
        ]
        for f in legacy_files:
            file_path = os.path.join(directory, f)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed legacy diagnostic artifact: {file_path}")
            except OSError as err:
                logger.warning(f"Could not remove legacy diagnostic file '{file_path}': {err}")
    except Exception as exc:
        logger.warning(f"Error during diagnostic folder cleanup: {exc}")


def export_to_json(data: Any, filename: str = "client_data.json") -> str:
    """
    Atomically export diagnostic telemetry snapshot to disk (Phase 9 I-05 / I-06).

    Guarantees:
    1. Writes to a temporary file in the same destination directory.
    2. Flushes and syncs data to disk before atomic replacement.
    3. Replaces previous snapshot via os.replace().
    4. Cleans up temporary file on failure without corrupting any existing snapshot.
    5. Retains ONE current snapshot; cleans obsolete timestamped artifacts.
    """
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    target_filepath = os.path.join(OUTPUT_FOLDER, filename)

    temp_filepath: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=OUTPUT_FOLDER,
            prefix=".tmp_diagnostic_",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as tf:
            temp_filepath = tf.name
            json.dump(
                data,
                tf,
                indent=4,
                default=lambda o: o.to_dict() if hasattr(o, "to_dict") else str(o),
            )
            tf.flush()
            os.fsync(tf.fileno())

        os.replace(temp_filepath, target_filepath)
        temp_filepath = None
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except OSError:
                pass

    clean_legacy_diagnostic_files(OUTPUT_FOLDER, keep_filename=filename)
    return target_filepath
