"""Tests for LLM Validation Toolkit"""

import pytest
from src.tools.llm_validation import LLMValidationMetrics


class TestLLMValidation:
    def test_confusion_matrix(self):
        """Test confusion matrix calculation"""
        metrics = LLMValidationMetrics()
        metrics.add_verdict('CONFIRM', 'CONFIRM')
        metrics.add_verdict('CONFIRM', 'CONTRADICT')
        metrics.add_verdict('CONTRADICT', 'CONTRADICT')
        
        cm = metrics.confusion_matrix()
        assert cm.loc['CONFIRM', 'CONFIRM'] == 1
        assert cm.loc['CONTRADICT', 'CONFIRM'] == 1
    
    def test_precision_recall(self):
        """Test precision/recall calculation"""
        metrics = LLMValidationMetrics()
        for _ in range(10):
            metrics.add_verdict('CONFIRM', 'CONFIRM')  # TP
        for _ in range(2):
            metrics.add_verdict('CONFIRM', 'CONTRADICT')  # FP
        for _ in range(3):
            metrics.add_verdict('CONTRADICT', 'CONFIRM')  # FN
        
        pr = metrics.precision_recall()
        assert pr['CONFIRM']['precision'] == 10/12  # TP/(TP+FP)
        assert pr['CONFIRM']['recall'] == 10/13  # TP/(TP+FN)
    
    def test_cohen_kappa(self):
        """Test Cohen's kappa calculation"""
        metrics = LLMValidationMetrics()
        # Perfect agreement
        for _ in range(10):
            metrics.add_verdict('CONFIRM', 'CONFIRM')
        
        kappa = metrics.cohen_kappa()
        assert kappa == 1.0  # Perfect agreement

