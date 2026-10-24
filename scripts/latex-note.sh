#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 -B "$ROOT_DIR/skills/notes-latex/scripts/notes_latex.py" "$@"
