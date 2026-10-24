#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 -B "$ROOT_DIR/skills/reviewer-latex/scripts/reviewer_latex.py" "$@"
