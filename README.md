# Prism LaTeX

Prism maintains project-local LaTeX workflows for research notes, existing peer-review reports, and academic manuscripts. Run the wrappers from this repository; the skills share its local build helpers and do not require global installation.

## 中文快速开始

```bash
scripts/latex-paper.sh --version
scripts/latex-paper.sh --list-templates
scripts/latex-paper.sh --check-deps
scripts/latex-paper.sh --init projects/Papers/demo --template prism
scripts/latex-paper.sh projects/Papers/demo --strict
```

`prism` 适合中英文科研草稿；`nature` 使用官方 `sn-jnl` / `sn-nature`，适合 Nature / NMI 初稿。两个模板都提供图表公式示例和独立补充材料。

```bash
scripts/latex-paper.sh --init projects/Papers/nature-demo --template nature
scripts/latex-paper.sh projects/Papers/nature-demo --strict
scripts/latex-paper.sh projects/Papers/nature-demo \
  --main supplementary.tex --strict --no-build-script
```

继续阅读：[中文使用指南](docs/guide.zh-CN.md) · [模板选型与官方来源](docs/templates.md) · [公开代码同步](docs/public-sync.md)。

## Workflows

- `notes-latex`: compile one Markdown, TXT, or TeX research note.
- `reviewer-latex`: format an existing review, separating confidential editor notes.
- `paper-latex`: initialize or compile a manuscript with sections, figures, and bibliography files.

Formatting preserves research claims and review judgments. Literature research, scientific analysis, and manuscript submission are separate tasks.

## Working directories

```text
skills/       Workflow instructions, templates, and entrypoints
scripts/      Three stable wrappers and lib/prism_latex shared helpers
tests/        Fixtures and local regression tests
projects/
  Notes/      Research notes, plans, and topic collections
  Papers/     Manuscript projects
  Reviews/    Journal / manuscript / original files
  External/   Links to external research projects
archives/     Dated local snapshots, retired tools, and historical material
```

Keep each manuscript and its attachments together under its journal. Preserve historical names, files, and build scripts; do not rebuild historical reviews as part of housekeeping. Unknown journals can stay in `Reviews/Others/` until identified. Full external project links belong under `External/`; document-specific links may stay with their workflow.

`projects/` and `archives/` are ignored, with only `projects/.gitkeep` tracked. Root-level `.bib` files are ignored and retained in place; bibliography files in maintained templates remain tracked. The 2026-09-30 migration manifest, file hashes, original entrypoint backups, and pre-change code snapshot are in `archives/2026-09-30/`.

## Requirements

- Python 3.9 or newer on macOS or Linux
- TeX Live with `latexmk`: XeLaTeX or LuaLaTeX for Prism/notes/reviews, pdfLaTeX and BibTeX for Nature
- Common packages such as `fontspec`, `microtype`, `hyperref`, `booktabs`, `tabularx`, `fancyhdr`, and `natbib`

The Prism template uses TeX Gyre and Fandol fonts; Nature retains its official class fonts. Nature initialization obtains a pinned official ZIP with SHA-256 verification; offline initialization accepts `--template-source PACKAGE.zip`. The upstream files remain in the generated local project and are not redistributed in this repository. DOCX review input optionally needs `python-docx`; text-based PDF input needs `pypdf` or `pdftotext`. TeX-only review export needs no LaTeX compiler. Dependency checks report missing commands, packages, and fonts without installing software:

```bash
scripts/latex-note.sh --check-deps
scripts/latex-review.sh --check-deps
scripts/latex-paper.sh --check-deps
scripts/latex-paper.sh projects/Papers/nature-demo --check-deps
```

In Codex desktop, open local single-file or multi-file LaTeX projects in the built-in editor and check them with native compilation when available. Use the project wrappers for template initialization, Markdown/TXT conversion, strict checks, and reproducible command-line builds.

## Usage

```bash
scripts/latex-note.sh path/to/note.md --strict

scripts/latex-review.sh path/to/review.md \
  --journal "Journal Name" --review-id "MS-XXXX" \
  --title "Paper title" --decision "Major Revision" --strict

scripts/latex-review.sh path/to/review.md --no-compile --outdir path/to/tex-output

scripts/latex-paper.sh --init path/to/new-paper
scripts/latex-paper.sh path/to/new-paper --strict
```

PDFs default beside the input or in the manuscript root. For reviews, `--outdir` selects the final output directory and `--out` overrides the author-facing output path. Editor notes use the `_editor_notes` suffix. `--no-compile` writes persistent `.tex` files using the corresponding output stem.

All compilation intermediates stay in temporary directories. `--strict` rejects missing glyphs, unresolved citations/references, and overfull boxes wider than the 2 pt tolerance. Use `--keep-work` only to debug a failed build; the command prints the retained directory. A failed review compilation preserves existing PDFs, including when editor-note compilation fails.

After a successful build, `prism-build.sh` records its input, output, and effective options:

```bash
cd path/to/project
./prism-build.sh
```

The script finds this repository locally. Use `PRISM_PROJECT_DIR` to select another Prism checkout; `PRISM_LATEX_SKILLS_DIR` remains supported for an explicit local skills path. It does not search global skill installations. `--no-build-script` suppresses creation. A matching managed script is refreshed; a conflicting script is preserved unless `--force-build-script` backs it up first.

Plugin installation, independent skill distribution, and release packaging have been retired to the dated archives. The maintained skills depend on this repository.

## Date versions and public code

`VERSION` is the single source of Prism's `YYYY.MM.DD` version; further versions on the same day append `.1`, `.2`. Dates use `Asia/Shanghai` and are updated manually when work completes. All three wrappers expose `--version` without requiring TeX. Git tags use `v2026.10.24`; upstream template versions remain separate.

Public synchronization uses a separate reviewed code snapshot and fresh history. Do not push this local repository's original history. Run `python3 -B scripts/export-public-code.py --check` and follow [the synchronization guide](docs/public-sync.md).

## Maintenance

Run `python3 -B -m unittest discover -s tests -v` after build behavior changes. Check all three wrapper help commands, compile representative fixtures in a temporary directory, and inspect rendered PDF pages for layout changes. Do not rebuild user research files for routine tests.

Record substantive changes under `Unreleased` in [CHANGELOG.md](CHANGELOG.md), then move completed entries into a dated section. Follow [AGENTS.md](AGENTS.md) for data preservation and Git checks.

Prism's own code and templates are licensed under the MIT License. Official files obtained when initializing Nature projects retain their upstream licensing.
