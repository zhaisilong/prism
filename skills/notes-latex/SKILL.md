---
name: notes-latex
description: Compile one research note from Markdown, TXT, or TeX into a clean PDF with the project-local Prism workflow. Use for single-file notes and mixed Chinese-English formatting; route multi-file manuscript projects to paper-latex.
---

# Notes LaTeX

Compile one note without changing its research claims or adding sources. This skill depends on the complete Prism repository and its shared implementation under `scripts/`.

## Workflow

1. Run the root wrapper from the Prism repository; from another directory, use its absolute path:

   ```bash
   scripts/latex-note.sh SOURCE
   ```

2. Keep the source in place. Write the PDF beside it unless `--out` is supplied.
3. After a successful wrapper build, retain and link the PDF and generated `prism-build.sh`. Show `cd "SOURCE_DIR" && ./prism-build.sh` to rebuild.
4. Inspect warnings and render representative pages when layout matters. Use `--strict` for delivery checks.
5. Use `--keep-work` only to diagnose a failed build.

## Inputs and options

- Accept `.md`, `.txt`, and `.tex`.
- Preserve a complete TeX document; wrap lightweight TeX fragments in the bundled note template.
- Support headings, paragraphs, lists, block quotes, fenced code, links, inline math, and simple pipe tables.
- Use `--title`, `--created-date`, `--updated-date`, `--out`, and `--engine auto|xelatex|lualatex` as needed.
- Use `--no-build-script` only when the user wants no reproducible project script. Use `--force-build-script` to back up and replace a conflicting `prism-build.sh`.
- Run `--check-deps` before building on a new machine.
- Use `--version` to read the repository's date version without TeX dependencies.
- Rebuild scripts locate this local Prism project. Set `PRISM_PROJECT_DIR` when the repository moves; the older `PRISM_LATEX_SKILLS_DIR` override remains supported. Do not install or modify global skills for this workflow.

## Standalone TeX in Codex desktop

When creating or editing TeX and the desktop editor is available, follow the host's built-in LaTeX workflow: open the saved source or local project with `open_in_codex`, then check compilation with `compile_latex_document`. Keep follow-up edits in that project. The native compiler supports local multi-file projects as well as standalone files. Use the wrapper for Markdown/TXT-to-PDF conversion and this workflow's reproducible builds.

## Boundary

- Do not turn notes into papers or reviewer reports.
- Do not add facts, citations, experimental conclusions, or bibliography entries.
- Do not parse DOCX, PDF, webpages, arbitrary Pandoc extensions, complex HTML, or nested tables.
- Route directories containing manuscript sections, figures, and bibliography files to `paper-latex`.

The build occurs in a temporary directory and copies back the final PDF plus the project-local reproducible build script.
