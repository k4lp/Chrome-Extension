#!/usr/bin/env python3
"""Convenience script to run GemBrain."""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gembrain.ui.app import main

if __name__ == "__main__":
    main()
