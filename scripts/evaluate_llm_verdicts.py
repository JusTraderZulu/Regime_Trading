#!/usr/bin/env python3
"""
Evaluate LLM Verdicts CLI

Analyzes LLM validation accuracy, generates metrics and diagnostics.

Usage:
    python scripts/evaluate_llm_verdicts.py --input data/llm_verdicts.json
    python scripts/evaluate_llm_verdicts.py --input data/verdicts.csv --output artifacts/llm_validation/
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.llm_validation import evaluate_llm_verdicts


def main():
    parser = argparse.ArgumentParser(description="Evaluate LLM verdict accuracy")
    parser.add_argument('--input', type=str, required=True, help='Input verdicts file (JSON or CSV)')
    parser.add_argument('--output', type=str, default='artifacts/llm_validation', help='Output directory')
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return 1
    
    print(f"Evaluating LLM verdicts from: {input_file}")
    metrics = evaluate_llm_verdicts(input_file, output_dir)
    
    print("\n✅ Evaluation complete!")
    print(f"Accuracy: {metrics['accuracy']:.1%}")
    print(f"Cohen's κ: {metrics['cohen_kappa']:.3f}")
    print(f"Results saved to: {output_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

