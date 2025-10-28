"""
LLM Validation Toolkit

Tools for evaluating LLM verdict accuracy, calibration, and consistency.
Includes confusion matrices, precision/recall, Cohen's kappa, and calibration plots.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class LLMValidationMetrics:
    """Metrics for LLM validation performance"""
    
    def __init__(self):
        self.verdicts = []  # List of (predicted, actual) tuples
        self.confidences = []  # List of confidence scores
    
    def add_verdict(self, predicted: str, actual: str, confidence: float = None):
        """Add a verdict for evaluation"""
        self.verdicts.append((predicted, actual))
        if confidence is not None:
            self.confidences.append(confidence)
    
    def confusion_matrix(self) -> pd.DataFrame:
        """Calculate confusion matrix"""
        if not self.verdicts:
            return pd.DataFrame()
        
        labels = sorted(set([v[0] for v in self.verdicts] + [v[1] for v in self.verdicts]))
        matrix = pd.DataFrame(0, index=labels, columns=labels)
        
        for pred, actual in self.verdicts:
            matrix.loc[actual, pred] += 1
        
        return matrix
    
    def precision_recall(self) -> Dict[str, Dict[str, float]]:
        """Calculate precision and recall per verdict type"""
        if not self.verdicts:
            return {}
        
        results = {}
        verdict_types = set([v[0] for v in self.verdicts] + [v[1] for v in self.verdicts])
        
        for verdict_type in verdict_types:
            tp = sum(1 for p, a in self.verdicts if p == verdict_type and a == verdict_type)
            fp = sum(1 for p, a in self.verdicts if p == verdict_type and a != verdict_type)
            fn = sum(1 for p, a in self.verdicts if p != verdict_type and a == verdict_type)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            results[verdict_type] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'support': tp + fn
            }
        
        return results
    
    def cohen_kappa(self) -> float:
        """Calculate Cohen's kappa for inter-rater agreement"""
        if not self.verdicts:
            return 0.0
        
        n = len(self.verdicts)
        
        # Observed agreement
        agree = sum(1 for p, a in self.verdicts if p == a)
        p_o = agree / n
        
        # Expected agreement by chance
        pred_counts = Counter([p for p, _ in self.verdicts])
        actual_counts = Counter([a for _, a in self.verdicts])
        
        p_e = sum(
            (pred_counts[label] / n) * (actual_counts[label] / n)
            for label in set(pred_counts.keys()) | set(actual_counts.keys())
        )
        
        # Kappa
        if p_e == 1.0:
            return 1.0  # Perfect agreement
        
        kappa = (p_o - p_e) / (1 - p_e)
        return kappa
    
    def calibration_curve(self, n_bins: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate calibration curve for confidence scores.
        
        Returns:
            Tuple of (bin_confidence, bin_accuracy)
        """
        if not self.confidences or len(self.confidences) != len(self.verdicts):
            return np.array([]), np.array([])
        
        # Bin by confidence
        bins = np.linspace(0, 1, n_bins + 1)
        bin_confidence = []
        bin_accuracy = []
        
        for i in range(n_bins):
            mask = [(bins[i] <= c < bins[i+1]) for c in self.confidences]
            if sum(mask) > 0:
                bin_conf = np.mean([c for c, m in zip(self.confidences, mask) if m])
                bin_acc = np.mean([1 if p==a else 0 for (p,a), m in zip(self.verdicts, mask) if m])
                bin_confidence.append(bin_conf)
                bin_accuracy.append(bin_acc)
        
        return np.array(bin_confidence), np.array(bin_accuracy)
    
    def export_metrics(self, output_path: Path):
        """Export metrics to JSON"""
        metrics = {
            'confusion_matrix': self.confusion_matrix().to_dict() if not self.confusion_matrix().empty else {},
            'precision_recall': self.precision_recall(),
            'cohen_kappa': self.cohen_kappa(),
            'n_verdicts': len(self.verdicts),
            'accuracy': sum(1 for p, a in self.verdicts if p == a) / len(self.verdicts) if self.verdicts else 0.0
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"✓ LLM metrics exported to {output_path}")
        
        return metrics


def evaluate_llm_verdicts(
    verdicts_file: Path,
    output_dir: Path
) -> Dict:
    """
    Evaluate LLM verdicts from a dataset file.
    
    Args:
        verdicts_file: Path to JSON/CSV with verdicts
        output_dir: Where to save metrics
        
    Returns:
        Metrics dictionary
    """
    metrics_calc = LLMValidationMetrics()
    
    # Load verdicts
    if verdicts_file.suffix == '.json':
        with open(verdicts_file) as f:
            data = json.load(f)
            for item in data:
                metrics_calc.add_verdict(
                    item['predicted'],
                    item['actual'],
                    item.get('confidence')
                )
    elif verdicts_file.suffix == '.csv':
        df = pd.read_csv(verdicts_file)
        for _, row in df.iterrows():
            metrics_calc.add_verdict(
                row['predicted'],
                row['actual'],
                row.get('confidence')
            )
    
    # Export metrics
    metrics = metrics_calc.export_metrics(output_dir / 'llm_metrics.json')
    
    return metrics

