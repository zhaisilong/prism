#!/usr/bin/env python3
"""Compatibility import for Prism's project-local shared implementation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_PROJECT_DIR = Path(os.environ.get("PRISM_PROJECT_DIR") or Path(__file__).resolve().parents[3]).expanduser().resolve()
_LIBRARY_DIR = _PROJECT_DIR / "scripts" / "lib"
if not (_LIBRARY_DIR / "prism_latex" / "build_script.py").is_file():
    raise SystemExit("Prism shared implementation was not found. Set PRISM_PROJECT_DIR to the Prism repository.")
if str(_LIBRARY_DIR) not in sys.path:
    sys.path.insert(0, str(_LIBRARY_DIR))

from prism_latex import build_script as _shared
from prism_latex.build_script import *


def __getattr__(name: str):
    return getattr(_shared, name)
