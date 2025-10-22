from collections import Counter
from typing import Dict, List, Literal

import numpy as np
import pandas as pd

Regime = Literal["trending", "mean_reverting", "random"]


def vote_labels_per_bar(labels_by_model: Dict[str, List[Regime]]) -> List[Regime]:
	"""Majority vote across models for each bar.

	Tie-breaker prefers previous consensus; falls back to "random" at start.
	All model lists must be the same length; missing/empty → treated as no vote.
	"""
	if not labels_by_model:
		return []
	# Determine length from first model present
	first = next(iter(labels_by_model.values()), [])
	n = len(first)
	if n == 0:
		return []
	out: List[Regime] = []
	for i in range(n):
		votes = Counter(m[i] for m in labels_by_model.values() if i < len(m))
		if not votes:
			out.append("random")
			continue
		top = votes.most_common()
		if len(top) > 1 and top[0][1] == top[1][1]:
			out.append(out[-1] if out else "random")
		else:
			out.append(top[0][0])
	return out


def compute_sigma_post_pre(returns: List[float], flip_indices: List[int], k: int) -> float:
	"""Compute pooled stdev ratio of post-flip vs pre-flip windows.

	returns: list aligned to ensemble labels window
	flip_indices: indices where label[i] != label[i-1]
	k: number of bars before/after each flip to include
	"""
	import math

	def stdev(xs: List[float]) -> float:
		if len(xs) < 2:
			return float("nan")
		m = sum(xs) / len(xs)
		return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))

	pre: List[float] = []
	post: List[float] = []
	for idx in flip_indices:
		if idx - k < 0 or idx + k >= len(returns):
			continue
		pre.extend(returns[idx - k : idx])
		post.extend(returns[idx + 1 : idx + 1 + k])

	sp, spo = stdev(pre), stdev(post)
	if not pre or not post or (sp != sp) or (spo != spo):  # NaN check
		return 1.0
	return float(spo / max(sp, 1e-12))


def _rolling_autocorr(x: pd.Series, lag: int, window: int) -> pd.Series:
	"""Causal rolling autocorrelation at given lag."""
	if len(x) < window + lag:
		return pd.Series(index=x.index, dtype=float)
	# Align series for lag
	x1 = x
	x2 = x.shift(lag)
	# Compute rolling correlation with pairwise valid alignment
	return x1.rolling(window, min_periods=max(5, lag + 1)).corr(x2)


def derive_heuristic_labels(df: pd.DataFrame, window: int = 50) -> Dict[str, List[Regime]]:
	"""Derive simple per-bar labels from close prices using causal heuristics.

	Models:
	- acf_model: rolling autocorr of returns at lag1
	- vr_like_model: ratio of rolling var of k-step return vs 1-step (proxy)
	- drift_model: rolling mean vs std threshold

	All outputs are aligned to df.index and returned as lists of strings.
	"""
	labels: Dict[str, List[Regime]] = {}
	if df is None or df.empty or "close" not in df:
		return {
			"acf_model": [],
			"vr_like_model": [],
			"drift_model": [],
		}

	# Keep alignment with df length; fill small gaps to avoid empty sequences
	close = pd.Series(pd.to_numeric(df["close"], errors="coerce"))
	close = close.ffill().bfill()
	if close.empty:
		return {
			"acf_model": [],
			"vr_like_model": [],
			"drift_model": [],
		}

	logret = np.log(close).diff().fillna(0.0)
	win = max(5, int(window))

	# ACF model
	acf1 = _rolling_autocorr(logret, lag=1, window=win)
	acf_lab = []
	for v in acf1.values:
		if pd.isna(v):
			acf_lab.append("random")
		elif v > 0.05:
			acf_lab.append("trending")
		elif v < -0.05:
			acf_lab.append("mean_reverting")
		else:
			acf_lab.append("random")

	# VR-like model (proxy): var of k-step over 1-step
	k = min(10, max(2, win // 5))
	ret1 = logret
	retk = logret.rolling(k).sum()
	var_k = retk.rolling(win, min_periods=5).var()
	var_1 = ret1.rolling(win, min_periods=5).var()
	vr = (var_k / (var_1 * max(k, 1))).replace([np.inf, -np.inf], np.nan)
	vr_lab = []
	for v in vr.values:
		if pd.isna(v):
			vr_lab.append("random")
		elif v > 1.02:
			vr_lab.append("trending")
		elif v < 0.98:
			vr_lab.append("mean_reverting")
		else:
			vr_lab.append("random")

	# Drift model: mean magnitude vs std
	mu = logret.rolling(win).mean()
	sd = logret.rolling(win).std(ddof=1)
	thr = 0.2
	drift_lab = []
	for m, s in zip(mu.values, sd.values):
		if pd.isna(m) or pd.isna(s) or s <= 0:
			drift_lab.append("random")
		elif abs(m) > thr * s:
			drift_lab.append("trending")
		else:
			drift_lab.append("random")

	# Align lengths to df length
	def _tail_to_len(seq: List[Regime], n: int) -> List[Regime]:
		if len(seq) >= n:
			return list(seq[-n:])
		# left pad with randoms if needed
		return ["random"] * (n - len(seq)) + list(seq)

	n = len(close)
	labels["acf_model"] = _tail_to_len(acf_lab, n)
	labels["vr_like_model"] = _tail_to_len(vr_lab, n)
	labels["drift_model"] = _tail_to_len(drift_lab, n)
	return labels


