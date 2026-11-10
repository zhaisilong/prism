"""Stable repository paths shared by catalog, initialization and workflows."""
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[3]
ASSET_DIR = PROJECT_DIR / "skills" / "paper-latex" / "assets"
METADATA_NAME = "prism-template.json"
