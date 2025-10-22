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

from src.core.schemas import ConflictFlags, RegimeDecision, RegimeLabel
from typing import Any

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

    base_confirmation = max(1, int(settings.get("confirmation_bars", 2)))
    use_transition = settings.get("use_transition_state", True)
    transition_conf_cap = float(settings.get("transition_confidence_cap", 0.4))

    symbol_key = decision.symbol
    tier_key = decision.tier.value

    tier_overrides_cfg = settings.get("tier_overrides", {})
    if not isinstance(tier_overrides_cfg, dict):  # Safety guard
        tier_overrides_cfg = {}
    tier_settings = tier_overrides_cfg.get(tier_key, {}) if isinstance(tier_overrides_cfg, dict) else {}

    gate_settings = decision.gates
    confirmation_bars = base_confirmation
    if gate_settings and gate_settings.m_bars:
        confirmation_bars = max(1, int(gate_settings.m_bars))
    elif isinstance(tier_settings, dict) and tier_settings.get("m_bars"):
        confirmation_bars = max(1, int(tier_settings["m_bars"]))

    gate_score = decision.posterior_p if decision.posterior_p is not None else decision.confidence
    gate_threshold = None
    if gate_settings and gate_settings.p_min is not None:
        gate_threshold = gate_settings.p_min
    elif isinstance(tier_settings, dict):
        gate_threshold = tier_settings.get("p_min")

    enter_threshold = tier_settings.get("enter") if isinstance(tier_settings, dict) else None
    exit_threshold = tier_settings.get("exit") if isinstance(tier_settings, dict) else None

    conflict_flags = decision.conflicts or ConflictFlags()
    conflict_flags.volatility_gate_block = False

    symbol_state = memory.setdefault(symbol_key, {})
    entry = symbol_state.get(tier_key, {})

    confirmed_label = _coerce_label(entry.get("confirmed_label"))
    pending_label = _coerce_label(entry.get("pending_label"))
    pending_count = int(entry.get("pending_count", 0))

    raw_label = decision.label
    raw_confidence = decision.confidence
    timestamp = decision.timestamp.isoformat()

    score_display = f"{gate_score:.2f}" if gate_score is not None else "n/a"

    # Gate-based deferral (dual thresholds / volatility scaling)
    gating_notes: list[str] = []
    if confirmed_label is not None and raw_label != confirmed_label:
        gating_blocked = False
        if gate_threshold is not None and (gate_score is None or gate_score < gate_threshold):
            gating_blocked = True
            gating_notes.append(f"score {score_display} < p_min {gate_threshold:.2f}")
        if enter_threshold is not None and (gate_score is None or gate_score < enter_threshold):
            gating_blocked = True
            gating_notes.append(f"score {score_display} < enter {enter_threshold:.2f}")
        if gating_blocked:
            has_pmin = any("p_min" in note for note in gating_notes)
            has_enter = any("enter" in note for note in gating_notes)
            has_exit = any("exit" in note for note in gating_notes)
            conflict_flags.volatility_gate_block = bool(has_pmin)
            if (has_enter or has_exit) and not has_pmin:
                conflict_flags.execution_blackout = True
            entry.update(
                {
                    "pending_label": confirmed_label.value,
                    "pending_count": 0,
                    "confirmation_required": confirmation_bars,
                    "last_updated": timestamp,
                }
            )
            rationale_note = "Gate blocked; " + "; ".join(gating_notes)
            final_conf = min(raw_confidence, transition_conf_cap)
            logger.info(
                "Gating defer: %s %s pending %s → %s (%s)",
                decision.symbol,
                tier_key,
                confirmed_label.value if confirmed_label else "n/a",
                raw_label.value,
                "; ".join(gating_notes),
            )
            adjusted = _annotate_decision(
                decision,
                final_label=confirmed_label,
                raw_label=raw_label,
                hysteresis_applied=True,
                confirmation_streak=0,
                confirmation_needed=confirmation_bars,
                info=rationale_note,
                override_confidence=final_conf,
                conflict_flags=conflict_flags,
                promotion_reason="gate_hold",
                gate_reasons=gating_notes,
            )
            symbol_state[tier_key] = entry
            return adjusted, memory
    elif exit_threshold is not None and gate_score is not None and gate_score < exit_threshold:
        conflict_flags.volatility_gate_block = True
        gating_notes.append(f"score {score_display} < exit {exit_threshold:.2f}")

    # First observation bootstrap
    if confirmed_label is None:
        entry.update(
            {
                "confirmed_label": raw_label.value,
                "pending_label": raw_label.value,
                "pending_count": confirmation_bars,
                "confirmation_required": confirmation_bars,
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
            conflict_flags=conflict_flags,
        )
        symbol_state[tier_key] = entry
        return adjusted, memory

    # If new observation matches confirmed label, reset counters
    if raw_label == confirmed_label:
        entry.update(
            {
                "pending_label": raw_label.value,
                "pending_count": confirmation_bars,
                "confirmation_required": confirmation_bars,
                "last_updated": timestamp,
            }
        )
        info_msg = "Matched confirmed regime"
        if gating_notes:
            info_msg += f" | {'; '.join(gating_notes)}"
        adjusted = _annotate_decision(
            decision,
            final_label=raw_label,
            raw_label=raw_label,
            hysteresis_applied=False,
            confirmation_streak=confirmation_bars,
            confirmation_needed=confirmation_bars,
            info=info_msg,
            conflict_flags=conflict_flags,
            gate_reasons=gating_notes if gating_notes else None,
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
            "confirmation_required": confirmation_bars,
            "last_updated": timestamp,
        }
    )

    if pending_count >= confirmation_bars:
        entry["confirmed_label"] = raw_label.value
        adjusted = _annotate_decision(
            decision,
            final_label=raw_label,
            raw_label=raw_label,
            hysteresis_applied=True,
            confirmation_streak=pending_count,
            confirmation_needed=confirmation_bars,
            info="Regime change confirmed via hysteresis",
            conflict_flags=conflict_flags,
            gate_reasons=gating_notes if gating_notes else None,
        )
    else:
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
            conflict_flags=conflict_flags,
            gate_reasons=gating_notes if gating_notes else None,
        )

    symbol_state[tier_key] = entry
    return adjusted, memory


def apply_adaptive_if_enabled(
    tier: str,
    base_gates: Any,
    suggestion: Any,
    config: Dict[str, Any],
) -> Any:
    """
    Optionally apply adaptive gates when feature flag is enabled.
    Safe: returns base_gates unchanged unless enabled.
    """
    try:
        features_cfg = config.get("features", {}) if isinstance(config, dict) else {}
        adaptive_cfg = features_cfg.get("adaptive_hysteresis", {}) if isinstance(features_cfg, dict) else {}
        if not adaptive_cfg.get("enabled", False):
            return base_gates
        # Build updated gates respecting the same type
        return base_gates.__class__(
            enter=getattr(suggestion, "suggest_enter", getattr(base_gates, "enter", None)),
            exit=getattr(suggestion, "suggest_exit", getattr(base_gates, "exit", None)),
            m_bars=getattr(suggestion, "suggest_m_bars", getattr(base_gates, "m_bars", None)),
            min_remaining=getattr(base_gates, "min_remaining", None),
        )
    except Exception:
        return base_gates


def _annotate_decision(
    decision: RegimeDecision,
    final_label: RegimeLabel,
    raw_label: RegimeLabel,
    hysteresis_applied: bool,
    confirmation_streak: int,
    confirmation_needed: int,
    info: str,
    override_confidence: float | None = None,
    conflict_flags: ConflictFlags | None = None,
    promotion_reason: str | None = None,
    gate_reasons: list[str] | None = None,
) -> RegimeDecision:
    """Return decision copy annotated with hysteresis metadata."""
    rationale_suffix = (
        f" | Hysteresis: raw={raw_label.value} → final={final_label.value} "
        f"(streak {confirmation_streak}/{confirmation_needed}; {info})"
    )

    updated_fields = {
        "label": final_label,
        "state": final_label.value,
        "base_label": raw_label,
        "hysteresis_applied": hysteresis_applied,
        "confirmation_streak": confirmation_streak,
        "rationale": decision.rationale + rationale_suffix,
    }

    if override_confidence is not None:
        updated_fields["confidence"] = override_confidence

    if promotion_reason is None and final_label != raw_label:
        promotion_reason = "hysteresis_holdover"

    if promotion_reason is not None:
        updated_fields["promotion_reason"] = promotion_reason

    if gate_reasons:
        updated_fields["gate_reasons"] = gate_reasons

    if conflict_flags is not None:
        updated_fields["conflicts"] = conflict_flags

    return decision.model_copy(update=updated_fields)


def _coerce_label(value: Any) -> RegimeLabel | None:
    """Coerce stored label string to RegimeLabel Enum."""
    if value is None:
        return None
    try:
        return RegimeLabel(value)
    except ValueError:
        return None
