"""Keep backend/fixtures/performance-history.json current.

The supplied generator writes daily history ending on the day it runs. If the file is missing, or
its newest date is before today, YTD/1D results would be wrong or empty, so we re-run the
generator at startup. If that isn't possible (e.g. Node not installed) we warn and carry on.
"""
import json
import logging
import shutil
import subprocess
from collections.abc import Callable
from datetime import date
from pathlib import Path

from app.config import HISTORY_GENERATOR

logger = logging.getLogger(__name__)


def latest_date(history_path: Path) -> date | None:
    """Newest snapshot date in the file, or None if missing/empty/unreadable."""
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        dates = [point["date"] for points in data.values() for point in points]
        return date.fromisoformat(max(dates)) if dates else None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def run_generator() -> None:
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is not on PATH.")
    subprocess.run([node, str(HISTORY_GENERATOR)], check=True, capture_output=True, timeout=30)


def ensure_history_file(history_path: Path, today: date, generate: Callable[[], None] = run_generator) -> None:
    newest = latest_date(history_path)
    if newest is not None and newest >= today:
        return
    reason = "missing or unreadable" if newest is None else f"stale (ends {newest})"
    try:
        generate()
        logger.info("Regenerated %s (was %s).", history_path, reason)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        logger.warning(
            "Performance history %s is %s and could not be regenerated (%s). "
            "Run `node backend/fixtures/generate-history.mjs`; history ranges may be empty until then.",
            history_path, reason, exc,
        )
