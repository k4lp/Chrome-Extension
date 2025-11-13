"""Main entry point for GemBrain."""

import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from gembrain.ui.app import main

if __name__ == "__main__":
    main()
