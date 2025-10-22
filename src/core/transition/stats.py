from .schema import TransitionStats, AdaptiveSuggestion


def suggest_hysteresis(
	stats: TransitionStats,
	base_m_bars: int,
	base_enter: float,
	base_exit: float,
	clamps: dict,
	formulas: dict,
	tier: str,
) -> AdaptiveSuggestion:
	"""Compute shadow-mode adaptive hysteresis suggestion with clamps.

	For Stage 1/2, z-score is treated as 0.0 (placeholder) to avoid behavior change.
	"""
	m_bars = int(
		max(
			clamps["m_bars_min"],
			min(clamps["m_bars_max"], formulas["m_bars_factor"] * max(1, stats.duration["median"]))
		)
	)
	z = 0.0
	enter_adj = min(clamps["enter_pp_max"], max(0.0, formulas["enter_pp_per_z"] * z))
	exit_adj = min(clamps["exit_pp_max"], max(0.0, formulas["exit_pp_per_z"] * z))
	return AdaptiveSuggestion(
		tier=tier,
		base_m_bars=base_m_bars,
		base_enter=base_enter,
		base_exit=base_exit,
		suggest_m_bars=m_bars,
		suggest_enter=base_enter + enter_adj,
		suggest_exit=base_exit + exit_adj,
		rationale=f"m_bars≈{formulas['m_bars_factor']}×median={stats.duration['median']:.0f}→{m_bars}; z={z:.2f}",
	)



