#!/usr/bin/env bash
set -Eeuo pipefail
PAPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${PRISM_PROJECT_DIR:?Set PRISM_PROJECT_DIR to the complete Prism repository}"
target="${1:-all}"
if [[ $# -gt 1 || ! "$target" =~ ^(main|si|all)$ ]]; then
  printf '%s\n' 'Usage: prism-build.sh [main|si|all]' >&2
  exit 2
fi
if [[ "$target" == main || "$target" == all ]]; then
  "$PRISM_PROJECT_DIR/scripts/latex-paper.sh" "$PAPER_DIR" \
    --main main.tex --engine xelatex --strict --no-build-script
fi
if [[ "$target" == si || "$target" == all ]]; then
  "$PRISM_PROJECT_DIR/scripts/latex-paper.sh" "$PAPER_DIR" \
    --main si.tex --engine xelatex --strict --no-build-script
fi
