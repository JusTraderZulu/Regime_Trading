from collections import deque, Counter
from typing import Deque, Optional, Tuple, Literal, Dict
import math

from .schema import TransitionStats, TransitionMatrix, HazardProfile

Regime = Literal["trending","mean_reverting","random"]


class TransitionTracker:
	"""
	Consumes per-bar regime labels and updates rolling metrics without mutating
	existing regime logic. Safe to run in parallel with current pipeline.
	"""

	def __init__(self, window_bars: int):
		self.window_bars = window_bars
		self.labels: Deque[Regime] = deque(maxlen=window_bars)
		self.runs: Deque[Tuple[Regime, int, int, int]] = deque()
		self._cur_label: Optional[Regime] = None
		self._cur_start: int = 0

	def ingest(self, label: Regime, idx: int):
		# idx = monotonic bar index (per tier)
		if self._cur_label is None:
			self._cur_label, self._cur_start = label, idx
		elif label != self._cur_label:
			# close old run
			run_len = idx - self._cur_start
			self.runs.append((self._cur_label, self._cur_start, idx - 1, run_len))
			self._cur_label, self._cur_start = label, idx
		self.labels.append(label)

	def _durations(self) -> Dict[str, float]:
		lens = [r[3] for r in list(self.runs)[-2000:]] or [0]
		lens_sorted = sorted(lens)
		def q(p: float) -> float:
			if not lens_sorted:
				return 0.0
			i = int(max(0, min(len(lens_sorted) - 1, p * (len(lens_sorted) - 1))))
			return float(lens_sorted[i])
		return {
			"mean": float(sum(lens) / max(1, len(lens))),
			"median": q(0.5),
			"p25": q(0.25),
			"p75": q(0.75),
		}

	def _flip_density(self) -> float:
		flips = sum(1 for i in range(1, len(self.labels)) if self.labels[i] != self.labels[i - 1])
		return float(flips / max(1, len(self.labels)))

	def _matrix(self) -> Dict[Regime, Dict[Regime, float]]:
		keys = ["trending", "mean_reverting", "random"]
		counts = {k: Counter() for k in keys}
		for i in range(1, len(self.labels)):
			a, b = self.labels[i - 1], self.labels[i]
			counts[a][b] += 1
		probs: Dict[Regime, Dict[Regime, float]] = {}
		for a in keys:
			total = sum(counts[a].values())
			probs[a] = {b: (counts[a][b] / total if total > 0 else 0.0) for b in keys}
		return probs

	def snapshot(self, tier: str, sigma_ratio: float = 1.0) -> TransitionStats:
		duration = self._durations()
		flip_density = self._flip_density()
		probs = self._matrix()
		entropy = -sum((p * math.log(p + 1e-12)) for a in probs for p in probs[a].values()) / 3.0
		alerts = []
		if flip_density > 0.02:
			alerts.append("flip_density_high")
		if duration["median"] < 3:
			alerts.append("duration_too_short")
		return TransitionStats(
			tier=tier,
			window_bars=self.window_bars,
			flip_density=flip_density,
			duration=duration,
			matrix=TransitionMatrix(probs=probs, entropy=float(entropy)),
			hazard=HazardProfile(h_t={1: 0.18, 5: 0.11, 10: 0.08}),
			sigma_around_flip_ratio=sigma_ratio,
			alerts=alerts,
		)


