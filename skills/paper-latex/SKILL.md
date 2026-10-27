---
name: paper-latex
description: Initialize or compile Prism, Nature, Nature Communications, BIB, DDT, JCIM, or Science Advances manuscripts with bibliography, figures, tables, equations, and supplementary material. Use for academic manuscript projects; route ordinary single-file notes to notes-latex.
---

# Paper LaTeX

Initialize or compile a manuscript draft without generating scientific content. This skill depends on the complete Prism repository and its shared implementation under `scripts/`. Read the [Chinese guide](../../docs/guide.zh-CN.md) for user-facing examples and [template sources](../../docs/templates.md) when choosing a journal template.

## Workflow

Run the root wrappers from the Prism repository; from another directory, use their absolute paths.

1. Initialize a new project when needed:

   ```bash
   scripts/latex-paper.sh --list-templates
   scripts/latex-paper.sh --init TARGET_DIR --template prism
   # For Nature / NMI drafts:
   scripts/latex-paper.sh --init TARGET_DIR --template nature
   # For a Nature Communications research paper:
   scripts/latex-paper.sh --init TARGET_DIR --template nature-communications
   # For Briefings in Bioinformatics:
   scripts/latex-paper.sh --init TARGET_DIR --template bib
   # For a Drug Discovery Today narrative review:
   scripts/latex-paper.sh --init TARGET_DIR --template ddt
   # For a JCIM research paper:
   scripts/latex-paper.sh --init TARGET_DIR --template jcim
   # For Science Advances, provide the official template directory or ZIP:
   scripts/latex-paper.sh --init TARGET_DIR --template science-advances --template-source PACKAGE
   ```

2. Replace author placeholders, example citations, and synthetic demonstration content. Prism uses `main.tex` plus `sections/`; journal starters keep the main text in one `main.tex`. All use `references.bib`.
3. Compile with:

   ```bash
   scripts/latex-paper.sh PAPER_DIR
   ```

4. Retain and link the PDF and generated `prism-build.sh` in the manuscript root. Show `cd "PAPER_DIR" && ./prism-build.sh` to rebuild.
5. Compile independent `supplementary.tex` or `examples.tex` with `--main FILE --no-build-script` to preserve the main rebuild script. Science Advances keeps supplementary material in `main.tex` to share bibliography numbering. Inspect the first page, references, dense figures/tables, equations, and representative pagination. Use `--strict` for delivery checks.

## Structure and options

- `prism` is the default `article` starter for English or mixed Chinese-English manuscripts. Its default engine remains XeLaTeX or LuaLaTeX.
- `prism-paper.sty` provides matched text/math fonts, consistent table and caption sizes, numeric columns, and multi-panel figures. Read [layout guidance](references/layout.md) when changing presentation or adapting an existing manuscript; the results and appendix sections contain working examples.
- `nature` uses official `sn-jnl` / `sn-nature` with pdfLaTeX and BibTeX. Initialization verifies a pinned official ZIP before changing the target; `--template-source PACKAGE.zip` supplies that ZIP offline. Keep downloaded official files in the local project with their original licensing; do not vendor them into the public source assets. Do not layer Prism typography over this class.
- `nature-communications` is an offline standard `article` research draft with BibTeX and independent supplementary material; consult the journal's requirements before preparing final TeX.
- `bib` means the journal Briefings in Bioinformatics. Use its official OUP class configuration, retaining journal typography and the numeric bibliography setup. Pinned official files stay in the generated project, with offline ZIP support through `--template-source`.
- `ddt` means Drug Discovery Today narrative-review drafts. Use the installed Elsevier `elsarticle` class and `elsarticle-num.bst`; initialization is offline. Keep optional highlights and teaser as separate draft placeholders, and check current journal requirements before submission.
- `jcim` is a research-paper draft using installed ACS `achemso` with BibTeX. Replace the TOC graphic placeholder and check current journal requirements; initialization is offline.
- `science-advances` imports the verified Science-family style files and copyright notice from a user-provided official directory or ZIP. Keep these upstream files local and unchanged; use one shared bibliography for main and supplementary text.
- The starters use numeric BibTeX citations; supplementary counters are independent. Read [layout guidance](references/layout.md) for rich examples. Thesis/book/proposal templates, CSL, Biber, and GB/T 7714 need project-specific configuration.
- Use `--main`, `--out`, `--engine auto|xelatex|lualatex|pdflatex`, `--strict`, and `--keep-work` as needed. Project template metadata lets `auto` select pdfLaTeX for journal starters without changing existing unmarked projects.
- Use `--no-build-script` only when the user wants no reproducible project script. Use `--force-build-script` to back up and replace a conflicting `prism-build.sh`.
- Run `scripts/latex-paper.sh PAPER_DIR --check-deps` for the initialized project's engine, local class, and resources; `--version` requires no TeX.
- Refuse to overwrite a non-empty initialization target unless `--force` creates a backup first.
- Rebuild scripts locate this local Prism project. Set `PRISM_PROJECT_DIR` when the repository moves; the older `PRISM_LATEX_SKILLS_DIR` override remains supported. Do not install or modify global skills for this workflow.

In Codex desktop, use the available built-in editor and native compiler for local single-file or multi-file TeX projects according to host instructions. Use the wrapper for this workflow's initialization, strict checks, temporary build isolation, and reproducible build scripts.

## Boundary

- Do not generate scientific claims, data, conclusions, or citations.
- Do not convert Markdown, DOCX, or PDF into a complete paper.
- Do not perform journal submission, plagiarism checking, literature search, or analysis execution.
- Nature/NMI support is for drafting and initial-submission PDFs. Consult current journal guidance before final source submission; no automatic flattening, macro removal, or bibliography embedding is provided.
- Route single-file research records to `notes-latex`.

The build occurs in a temporary directory and copies back the final PDF plus the project-local reproducible build script.
