from typing import Dict, Literal, List, Optional
from pydantic import BaseModel

Regime = Literal["trending","mean_reverting","random"]


class TransitionMatrix(BaseModel):
	probs: Dict[Regime, Dict[Regime, float]]
	entropy: float


class HazardProfile(BaseModel):
	h_t: Dict[int, float]


class TransitionStats(BaseModel):
	tier: Literal["LT","MT","ST","US"]
	window_bars: int
	flip_density: float
	duration: Dict[str, float]
	matrix: TransitionMatrix
	hazard: HazardProfile
	sigma_around_flip_ratio: float
	pnl_slice: Optional[Dict[str, float]] = None
	alerts: List[str] = []


class AdaptiveSuggestion(BaseModel):
	tier: Literal["LT","MT","ST","US"]
	base_m_bars: int
	base_enter: float
	base_exit: float
	suggest_m_bars: int
	suggest_enter: float
	suggest_exit: float
	rationale: str


