---
name: reviewer-latex
description: Format an existing academic peer-review draft from Markdown, TXT, DOCX, or a text-based PDF into an author-facing PDF and optional separate confidential editor-notes PDF. Use for restructuring reviewer metadata and Overall, Major, and Minor comments without changing the reviewer's scientific judgment.
---

# Reviewer LaTeX

Format an existing review while preserving its scientific wording. This skill depends on the complete Prism repository and its shared implementation under `scripts/`.

## Workflow

1. Identify journal, manuscript ID, title, recommendation, Overall Comments, Major Concerns, Minor Concerns, and optional editor-only notes.
2. Run the root wrapper from the Prism repository; from another directory, use its absolute path:

   ```bash
   scripts/latex-review.sh INPUT \
     --journal "Journal Name" --review-id "MS-XXXX" \
     --title "Paper title" --decision "Major Revision"
   ```

3. Confirm confidential notes appear only in the `_editor_notes.pdf` output.
4. Retain and link the PDF outputs and generated `prism-build.sh` beside the input. Show `cd "INPUT_DIR" && ./prism-build.sh` to rebuild.
5. Inspect warnings and rendered pages. Use `--strict` for delivery checks.

## Inputs and behavior

- Accept `.md`, `.txt`, `.docx`, or a text-based `.pdf`.
- Require optional `python-docx` for DOCX input. For PDF, use `pypdf` or the `pdftotext` command.
- Read [template notes](references/template-notes.md) when mapping metadata or section headings; check that editor-only material is classified correctly before export.
- Keep Major and Minor point numbering continuous.
- Use `--outdir` for the final output directory; `--out` takes precedence for the author-facing output path. Metadata overrides, `--date`, and `--engine auto|xelatex|lualatex` remain available.
- Use `--no-compile` for persistent author-facing TeX and optional separate editor-notes TeX. This mode needs no LaTeX compiler and creates no PDF or build script.
- Use `--no-build-script` only when the user wants no reproducible project script. Use `--force-build-script` to back up and replace a conflicting `prism-build.sh`.
- Run `--check-deps` on a new machine.
- Use `--version` to read the repository's date version without TeX dependencies.
- Rebuild scripts locate this local Prism project. Set `PRISM_PROJECT_DIR` when the repository moves; the older `PRISM_LATEX_SKILLS_DIR` override remains supported. Do not install or modify global skills for this workflow.

When editing a TeX report in Codex desktop, open the saved source or local project with `open_in_codex` and check it with `compile_latex_document`, following host instructions. The native compiler supports local multi-file projects. Use the wrapper to convert Markdown, TXT, DOCX, or PDF reviews and to preserve this workflow's author/editor separation and reproducible builds.

## Boundary

- Do not invent review findings, references, decisions, or editor comments.
- Do not strengthen or weaken the reviewer's judgment unless the user explicitly asks for content editing.
- Do not OCR scanned PDFs or act as a general DOCX/PDF converter.
- Do not upload to submission systems, send messages, or decide anonymity policy.
- Route manuscript projects to `paper-latex` and ordinary notes to `notes-latex`.

The build occurs in a temporary directory and copies back final PDFs plus the project-local reproducible build script.
