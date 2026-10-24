# Agent Guide

Prism maintains local LaTeX workflows. Use this guide for project work and future automation.

## Source of truth

- Maintain workflow instructions and templates under `skills/`; share build implementations through `scripts/lib/prism_latex/`.
- Prefer `scripts/latex-note.sh`, `scripts/latex-review.sh`, and `scripts/latex-paper.sh` over global tools or ad hoc compiler commands.
- Skill-local `build_support.py` and `build_script.py` are compatibility shims. Change the shared implementation instead of duplicating it.
- Do not recreate or rely on the deleted global reviewer-latex skill. Do not install or modify global Codex skills for Prism.
- This is a local Git repository. Add remotes, publishing workflows, or distribution functionality only when the user requests them.
- Authorized public synchronization uses an audited export and independent Git history; never push this research checkout's original history. See `docs/public-sync.md` and `scripts/export-public-code.py`.

## Local data and directory policy

- `projects/Notes/` contains notes, plans, and topic collections; `Papers/` contains manuscripts; `Reviews/` uses journal/manuscript folders; `External/` contains links to external projects.
- Preserve filenames and attachments inside each research project. Keep unknown review journals in `Reviews/Others/` until identified.
- `projects/` is ignored; its only tracked file is `projects/.gitkeep`.
- `archives/` is ignored in full. It contains dated snapshots, retired tools, old templates, historical material, and migration manifests. Do not add a tracked archive placeholder.
- Root `.bib` files remain ignored local resources. Bibliographies inside maintained templates are tracked.
- Preserve research content and generated PDFs. Do not stage local research, archives, or project symlinks unless the user explicitly changes this policy.
- Historical reviews, including their build scripts, are immutable during housekeeping: do not edit or execute them. Scientific Reports historical material is in the dated archives.
- When moving data, inventory paths, sizes, hashes, and link targets; verify copies before retiring originals. Refuse collisions and stop if source files change.

## Build entrypoints

```bash
scripts/latex-note.sh SOURCE
scripts/latex-review.sh SOURCE
scripts/latex-paper.sh PAPER_DIR
```

All PDF builds use temporary directories and publish final PDFs plus an optional `prism-build.sh`. Review `--no-compile` exports persistent TeX without requiring a compiler. `--outdir` is a review output directory; `--out` takes precedence.

Generated scripts use local project discovery and support `PRISM_PROJECT_DIR` and the existing `PRISM_LATEX_SKILLS_DIR` override. Preserve an unrelated script unless explicit force requests a backup and replacement.

For TeX creation/editing in Codex desktop, follow the host's built-in editor and native compiler workflow for local single-file or multi-file projects when available. Use the project wrappers for template initialization, Markdown/TXT conversion, strict checks, and reproducible builds.

## Clean builds and workflow changes

- Keep source directories free of newly generated `.aux`, `.log`, `.fls`, `.fdb_latexmk`, `.out`, `.bbl`, `.blg`, and `.toc` files. Do not sweep historical reviews or delete research material to achieve cleanliness.
- Use `--keep-work` only for failed-build debugging and tell the user the retained temporary path.
- Add new workflows under `skills/<name>/`, with a concise `SKILL.md`, reusable `assets/`, and workflow-specific scripts only when needed. Provide a stable root wrapper for direct use.
- Describe current dependency defaults accurately; richer journal, bibliography, or document requirements can be added when justified.
- Update `CHANGELOG.md` for each substantive workflow, directory-policy, or build change. Use `Unreleased` during work and dated entries for completed changes. Avoid private review details in tracked documentation.
- Maintain Prism's date version in root `VERSION` (`YYYY.MM.DD`, then `.1`, `.2` for further same-day versions), using `Asia/Shanghai`. Keep upstream template versions and TeX package edit dates separate.

## Verification

```bash
scripts/latex-note.sh --help
scripts/latex-review.sh --help
scripts/latex-paper.sh --help
python3 -B -m unittest discover -s tests -v
```

For PDF-producing changes, compile copied or synthetic fixtures in temporary directories and visually inspect the first page and representative pagination. Cover confidentiality, bibliography resolution, failure preservation, and source-directory cleanliness where relevant. Never use historical research PDFs as build-test outputs.

Before committing, verify that local data stays untracked:

```bash
git status --short --ignored
git ls-files | rg '^(projects|archives|latex-templates|Latex-tmplates-todo)/|^[^/]+\.bib$'
```

The second command must only print `projects/.gitkeep`. Do not reset existing user changes or commit unless requested.
