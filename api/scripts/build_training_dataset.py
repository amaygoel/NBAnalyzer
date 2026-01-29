#!/usr/bin/env python3
"""
CLI script to build margin prediction training dataset.
Run from api/ directory: ./venv/bin/python scripts/build_training_dataset.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nb_analyzer.ml.dataset_builder import main

if __name__ == '__main__':
    main()
