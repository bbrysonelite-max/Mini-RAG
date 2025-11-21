"""Pytest configuration shared across SDK and contract tests."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT_STR = str(PROJECT_ROOT)
if PROJECT_ROOT_STR not in sys.path:
    # Ensure local (non-packaged) modules such as `server` and `clients.sdk`
    # remain importable when pytest adjusts the working directory.
    sys.path.insert(0, PROJECT_ROOT_STR)

