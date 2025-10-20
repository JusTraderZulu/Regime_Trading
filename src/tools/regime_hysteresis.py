"""
Utilities for applying regime hysteresis (confirmation logic and transition states).

Stores lightweight regime memory on disk so consecutive pipeline runs can confirm
regime changes before switching strategies.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

from src.core.schemas import RegimeDecision, RegimeLabel

logger = logging.getLogger(__name__)

STATE_PATH = Path("data/state/regime_memory.json")


def load_regime_memory(path: Path = STATE_PATH) -> Dict[str, Any]:
    """Load persisted regime memory."""
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning(f"Failed to load regime memory ({exc}), starting fresh")
        return {}


def save_regime_memory(memory: Dict[str, Any], path: Path = STATE_PATH) -> None:
    """Persist regime memory to disk."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(memory, fh, indent=2)
    except Exception as exc:
        logger.warning(f"Failed to persist regime memory: {exc}")


def apply_hysteresis(
    decision: RegimeDecision,
    memory: Dict[str, Any],
    settings: Dict[str, Any],
) -> Tuple[RegimeDecision, Dict[str, Any]]:
    """
    Apply confirmation-based hysteresis to a regime decision.

    Args:
        decision: Raw regime decision produced by classifier.
        memory: Persistent memory dict (mutable).
        settings: Hysteresis configuration.

    Returns:
        (possibly adjusted decision, updated memory)
    """
    if not settings.get("enabled", False):
        return decision, memory

    confirmation_bars = max(1, int(settings.get("confirmation_bars", 2)))
    use_transition = settings.get("use_transition_state", True)
    transition_conf_cap = float(settings.get("transition_confidence_cap", 0.4))

    symbol_key = decision.symbol
    tier_key = decision.tier.value

    symbol_state = memory.setdefault(symbol_key, {})
    entry = symbol_state.get(tier_key, {})

    confirmed_label = _coerce_label(entry.get("confirmed_label"))
    pending_label = _coerce_label(entry.get("pending_label"))
    pending_count = int(entry.get("pending_count", 0))

    raw_label = decision.label
    raw_confidence = decision.confidence
    timestamp = decision.timestamp.isoformat()

    # First observation bootstrap
    if confirmed_label is None:
        entry.update(
            {
                "confirmed_label": raw_label.value,
                "pending_label": raw_label.value,
                "pending_count": confirmation_bars,
                "last_updated": timestamp,
            }
        )
        adjusted = _annotate_decision(
            decision,
            final_label=raw_label,
            raw_label=raw_label,
            hysteresis_applied=False,
            confirmation_streak=confirmation_bars,
            confirmation_needed=confirmation_bars,
            info="Initial regime confirmation bootstrap",
        )
        symbol_state[tier_key] = entry
        return adjusted, memory

    # If new observation matches confirmed label, reset counters
    if raw_label == confirmed_label:
        entry.update(
            {
                "pending_label": raw_label.value,
                "pending_count": confirmation_bars,
                "last_updated": timestamp,
            }
        )
        adjusted = _annotate_decision(
            decision,
            final_label=raw_label,
            raw_label=raw_label,
            hysteresis_applied=False,
            confirmation_streak=confirmation_bars,
            confirmation_needed=confirmation_bars,
            info="Matched confirmed regime",
        )
        symbol_state[tier_key] = entry
        return adjusted, memory

    # Otherwise we are observing a potential regime change
    if raw_label == pending_label:
        pending_count += 1
    else:
        pending_label = raw_label
        pending_count = 1

    entry.update(
        {
            "pending_label": pending_label.value,
            "pending_count": pending_count,
            "last_updated": timestamp,
        }
    )

    if pending_count >= confirmation_bars:
        # Confirm the new regime
        entry["confirmed_label"] = raw_label.value
        adjusted = _annotate_decision(
            decision,
            final_label=raw_label,
            raw_label=raw_label,
            hysteresis_applied=True,
            confirmation_streak=pending_count,
            confirmation_needed=confirmation_bars,
            info="Regime change confirmed via hysteresis",
        )
    else:
        # Stay in transition / retain previous confirmed regime
        final_label = RegimeLabel.UNCERTAIN if use_transition else confirmed_label
        final_conf = min(raw_confidence, transition_conf_cap)
        rationale_note = (
            f"Hysteresis holding prior regime ({confirmed_label.value if confirmed_label else 'n/a'}); "
            f"pending {pending_label.value} {pending_count}/{confirmation_bars}"
        )
        adjusted = _annotate_decision(
            decision,
            final_label=final_label,
            raw_label=raw_label,
            hysteresis_applied=True,
            confirmation_streak=pending_count,
            confirmation_needed=confirmation_bars,
            info=rationale_note,
            override_confidence=final_conf,
        )

    symbol_state[tier_key] = entry
    return adjusted, memory


def _annotate_decision(
    decision: RegimeDecision,
    final_label: RegimeLabel,
    raw_label: RegimeLabel,
    hysteresis_applied: bool,
    confirmation_streak: int,
    confirmation_needed: int,
    info: str,
    override_confidence: float | None = None,
) -> RegimeDecision:
    """Return decision copy annotated with hysteresis metadata."""
    rationale_suffix = (
        f" | Hysteresis: raw={raw_label.value} → final={final_label.value} "
        f"(streak {confirmation_streak}/{confirmation_needed}; {info})"
    )

    updated_fields = {
        "label": final_label,
        "base_label": raw_label,
        "hysteresis_applied": hysteresis_applied,
        "confirmation_streak": confirmation_streak,
        "rationale": decision.rationale + rationale_suffix,
    }

    if override_confidence is not None:
        updated_fields["confidence"] = override_confidence

    return decision.model_copy(update=updated_fields)


def _coerce_label(value: Any) -> RegimeLabel | None:
    """Coerce stored label string to RegimeLabel Enum."""
    if value is None:
        return None
    try:
        return RegimeLabel(value)
    except ValueError:
        return None

