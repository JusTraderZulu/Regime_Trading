from collections import deque, Counter
from typing import Deque, Optional, Tuple, Literal, Dict
import math
import numpy as np

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

	def ingest_sequence(self, labels: list[Regime]):
		"""Replace current window with a full sequence and rebuild runs."""
		# Reset
		self.labels.clear()
		self.runs.clear()
		self._cur_label = None
		self._cur_start = 0
		for i, l in enumerate(labels):
			self.ingest(l, i)

	def _durations(self) -> Dict[str, float]:
		# Compute run lengths from the current label window (include ongoing run)
		lab = list(self.labels)
		if not lab:
			return {"mean": 0.0, "median": 0.0, "p25": 0.0, "p75": 0.0}
		lens: list[int] = []
		cur = lab[0]
		length = 1
		for l in lab[1:]:
			if l == cur:
				length += 1
			else:
				lens.append(length)
				cur = l
				length = 1
		# close final run
		lens.append(length)
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
	
	def _wilson_interval(self, successes: int, trials: int, alpha: float = 0.05) -> Dict[str, float]:
		"""
		Wilson score interval for binomial proportion (e.g., flip density).
		More accurate than normal approximation for small samples.
		
		Args:
			successes: Number of successes (flips)
			trials: Total trials (bars)
			alpha: Significance level (0.05 for 95% CI)
			
		Returns:
			Dict with 'lower' and 'upper' bounds
		"""
		if trials == 0:
			return {'lower': 0.0, 'upper': 0.0}
		
		p = successes / trials
		z = 1.96  # 95% CI (for alpha=0.05)
		
		denominator = 1 + z**2 / trials
		center = (p + z**2 / (2*trials)) / denominator
		margin = z * math.sqrt(p*(1-p)/trials + z**2/(4*trials**2)) / denominator
		
		return {
			'lower': max(0.0, center - margin),
			'upper': min(1.0, center + margin)
		}
	
	def _bootstrap_median_duration_ci(self, n_bootstrap: int = 1000, alpha: float = 0.05) -> Dict[str, float]:
		"""
		Bootstrap confidence interval for median duration.
		
		Args:
			n_bootstrap: Number of bootstrap samples
			alpha: Significance level (0.05 for 95% CI)
			
		Returns:
			Dict with 'lower' and 'upper' bounds
		"""
		if not self._runs:
			return {'lower': 0.0, 'upper': 0.0}
		
		# Get run durations
		durations = [run[2] for run in self._runs]  # run = (start, end, length, label)
		
		# Bootstrap resampling
		medians = []
		for _ in range(n_bootstrap):
			sample = np.random.choice(durations, size=len(durations), replace=True)
			medians.append(np.median(sample))
		
		# Percentile method
		lower_pct = (alpha / 2) * 100
		upper_pct = (1 - alpha / 2) * 100
		
		return {
			'lower': float(np.percentile(medians, lower_pct)),
			'upper': float(np.percentile(medians, upper_pct))
		}
	
	def _bootstrap_entropy_ci(self, probs: Dict, n_bootstrap: int = 1000, alpha: float = 0.05) -> Dict[str, float]:
		"""
		Bootstrap confidence interval for entropy.
		Resamples transitions to estimate entropy uncertainty.
		
		Args:
			probs: Current transition matrix
			n_bootstrap: Number of bootstrap samples
			alpha: Significance level
			
		Returns:
			Dict with 'lower' and 'upper' bounds
		"""
		if len(self.labels) < 2:
			return {'lower': 0.0, 'upper': 0.0}
		
		# Get transitions
		transitions = [(self.labels[i-1], self.labels[i]) for i in range(1, len(self.labels))]
		
		# Bootstrap
		entropies = []
		for _ in range(n_bootstrap):
			# Resample transitions
			sample = [transitions[i] for i in np.random.randint(0, len(transitions), len(transitions))]
			
			# Build transition matrix from sample
			keys = ["trending", "mean_reverting", "random"]
			counts = {k: Counter() for k in keys}
			for (a, b) in sample:
				counts[a][b] += 1
			
			# Calculate entropy
			row_ents = []
			for from_state in keys:
				total = sum(counts[from_state].values())
				if total > 0:
					row_ent = 0.0
					for to_state in keys:
						p = counts[from_state][to_state] / total
						if p > 0:
							row_ent += -p * math.log(p)
					row_ents.append(row_ent)
			
			if row_ents:
				entropies.append(sum(row_ents) / len(row_ents))
		
		if not entropies:
			return {'lower': 0.0, 'upper': 0.0}
		
		# Percentile method
		lower_pct = (alpha / 2) * 100
		upper_pct = (1 - alpha / 2) * 100
		
		return {
			'lower': float(np.percentile(entropies, lower_pct)),
			'upper': float(np.percentile(entropies, upper_pct))
		}

	def snapshot(self, tier: str, sigma_ratio: float = 1.0, compute_ci: bool = True) -> TransitionStats:
		duration = self._durations()
		flip_density = self._flip_density()
		probs = self._matrix()
		# Compute average row entropy (standard for Markov chains)
		row_entropies = []
		for from_state in probs:
			row_ent = -sum(p * math.log(p) for p in probs[from_state].values() if p > 0)
			row_entropies.append(row_ent)
		entropy = sum(row_entropies) / len(row_entropies) if row_entropies else 0.0
		
		# Count transitions (sample size)
		n_transitions = sum(1 for i in range(1, len(self.labels)) if self.labels[i] != self.labels[i-1])
		sample_size = len(self.labels)
		
		# Compute confidence intervals if requested
		flip_density_ci = None
		median_duration_ci = None
		entropy_ci = None
		
		if compute_ci and sample_size > 0:
			# Wilson interval for flip density (binomial proportion)
			flip_density_ci = self._wilson_interval(n_transitions, sample_size)
			
			# Bootstrap CI for median duration
			if len(self._runs) >= 10:  # Need enough runs for bootstrap
				median_duration_ci = self._bootstrap_median_duration_ci()
			
			# Bootstrap CI for entropy
			if len(self.labels) >= 30:  # Need enough data
				entropy_ci = self._bootstrap_entropy_ci(probs)
		
		alerts = []
		if flip_density > 0.15:  # Raised from 0.02 (2% too sensitive)
			alerts.append("flip_density_high")
		if duration["median"] < 2:  # Lowered from 3 bars
			alerts.append("duration_too_short")
		return TransitionStats(
			tier=tier,
			window_bars=self.window_bars,
			flip_density=flip_density,
			duration=duration,
			matrix=TransitionMatrix(probs=probs, entropy=float(entropy)),
			hazard=HazardProfile(h_t={1: 0.18, 5: 0.11, 10: 0.08}),  # TODO: compute empirically
			sigma_around_flip_ratio=sigma_ratio,
			alerts=alerts,
			flip_density_ci=flip_density_ci,
			median_duration_ci=median_duration_ci,
			entropy_ci=entropy_ci,
			sample_size=sample_size,
		)


