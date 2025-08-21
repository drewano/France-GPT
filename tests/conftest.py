"""
Configuration file for pytest.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import modules from it
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
