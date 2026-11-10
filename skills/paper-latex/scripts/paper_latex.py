#!/usr/bin/env python3
"""Compatibility entrypoint for the repository's paper workflow."""
from __future__ import annotations
import os
from pathlib import Path
import sys

_PROJECT_DIR = Path(os.environ.get("PRISM_PROJECT_DIR") or Path(__file__).resolve().parents[3]).expanduser().resolve()
_LIBRARY_DIR = _PROJECT_DIR / "scripts/lib"
if not (_LIBRARY_DIR / "prism_latex/paper.py").is_file():
    raise SystemExit("Prism shared implementation was not found. Set PRISM_PROJECT_DIR to the Prism repository.")
if str(_LIBRARY_DIR) not in sys.path:
    sys.path.insert(0, str(_LIBRARY_DIR))
from prism_latex import paper as _shared
from prism_latex.paper import *


def __getattr__(name):
    return getattr(_shared, name)


if __name__ == "__main__":
    sys.exit(main())
