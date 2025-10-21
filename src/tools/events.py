"""Macro event utilities for gating and reporting."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pytz

logger = logging.getLogger(__name__)


def _ensure_datetime(value: Any) -> datetime | None:
    """Parse ISO-8601 string to timezone-aware UTC datetime."""
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    else:
        dt = dt.astimezone(pytz.UTC)
    return dt


def load_macro_events(calendar_paths: List[str]) -> List[Dict[str, Any]]:
    """Load macro event calendars from disk.

    Args:
        calendar_paths: List of JSON file paths containing events.

    Returns:
        List of events with UTC start/end timestamps and severity tag.
    """

    events: List[Dict[str, Any]] = []

    for path_str in calendar_paths:
        path = Path(path_str)
        if not path.exists():
            logger.debug("Event calendar missing: %s", path)
            continue

        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as exc:
            logger.warning("Failed to load events from %s: %s", path, exc)
            continue

        for item in payload:
            start = _ensure_datetime(item.get("start"))
            end = _ensure_datetime(item.get("end") or item.get("start"))
            if not start:
                continue
            if not end:
                end = start + timedelta(minutes=30)

            events.append(
                {
                    "name": item.get("name", "event"),
                    "start": start,
                    "end": end,
                    "severity": str(item.get("severity", "medium")).lower(),
                    "source": str(path),
                }
            )

    return events


def active_events(
    timestamp: datetime,
    events: List[Dict[str, Any]],
    lead_minutes: int,
    trail_minutes: int,
    severity_floor: str = "high",
) -> List[Dict[str, Any]]:
    """Return events active within the blackout window around timestamp."""

    if not events:
        return []

    severity_rank = {"low": 0, "medium": 1, "high": 2}
    threshold = severity_rank.get(severity_floor.lower(), 1)

    ts = timestamp if timestamp.tzinfo else pytz.UTC.localize(timestamp)
    window_start = ts - timedelta(minutes=lead_minutes)
    window_end = ts + timedelta(minutes=trail_minutes)

    active: List[Dict[str, Any]] = []
    for event in events:
        severity = severity_rank.get(str(event.get("severity", "medium")).lower(), 1)
        if severity < threshold:
            continue

        start = event.get("start")
        end = event.get("end")
        if not start or not end:
            continue

        if start <= window_end and end >= window_start:
            active.append(event)

    return active
