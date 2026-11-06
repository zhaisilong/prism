---
name: paper-latex
description: Initialize or compile academic LaTeX manuscripts using Prism journal templates, bibliography, figures, tables, equations, and supplementary material. Use for manuscript projects; route ordinary single-file notes to notes-latex.
---

# Paper LaTeX

Use the complete Prism repository as the source of truth. Run its root wrapper by absolute path when outside the repository; the installed skill is only an entrypoint. Respect `PRISM_PROJECT_DIR` when the repository has moved. Never fall back to an older installed copy of the build implementation.

## Create and build

```bash
scripts/latex-paper.sh --list-templates
scripts/latex-paper.sh --init TARGET_DIR --template TEMPLATE
scripts/latex-paper.sh TARGET_DIR --strict
```

All default starters initialize offline from repository assets and support mixed Chinese and English in titles, text, figures, tables, and supplementary material. Journal starters use XeLaTeX; the generic Prism starter supports XeLaTeX and LuaLaTeX. Use `--language english` at initialization to retain the journal's original pdfLaTeX mode. Bibliography entries remain English. Choose a template from the list rather than maintaining a second catalog here. Read [template sources](../../docs/templates.md) for journal-specific structure, citation styles, and upstream licensing; read the [short Chinese guide](../../docs/guide.zh-CN.md) for user-facing instructions.

- Edit the existing project's content in place. Replace demonstration text, authors, and citations before delivery; do not invent scientific claims, data, or references.
- Preserve the main `prism-build.sh` when compiling independent supplements or examples: use `--main supplementary.tex --no-build-script` or `--main examples.tex --no-build-script`. Science Advances combines its supplement with the main text.
- Inspect the first page, references, dense figures/tables, and representative pagination. Read [layout guidance](references/layout.md) when adjusting presentation.
- Link the final PDF and show `cd "TARGET_DIR" && ./prism-build.sh` for rebuilding. Builds use temporary directories; a failed build preserves the previous PDF. Use `--keep-work` only for debugging and report the retained path.

## Options and boundaries

- `--check-deps` checks the initialized project's engine and resources; `--version` needs no TeX. Missing dependencies should be reported, not silently installed.
- Initialization refuses a nonempty directory unless explicitly requested with `--force`, which backs it up. Preserve unrelated build scripts unless `--force-build-script` is requested.
- Nature defaults to a Prism-maintained `article` draft. Existing `sn-jnl` projects remain supported; explicit local official import uses `--template-source`. Read [advanced usage](../../docs/reference.zh-CN.md) only when needed.
- Existing projects keep their original engine and TeX source. If asked to enable bilingual text in an existing manuscript, follow the documented manual setup and use the explicit engine; do not silently rewrite manuscript sources or replace unrelated rebuild scripts.
- Install or update the local entrypoint only when requested, using `scripts/install-paper-skill.py`. Do not copy the shared implementation into global skills or modify other skills.
- Keep research files and local installation paths private. Do not submit manuscripts, publish research, or upload project contents as part of formatting.
- Route single-file notes to `notes-latex` and existing peer-review drafts to `reviewer-latex`. Do not convert a Markdown, DOCX, or PDF document into a complete scientific paper.

For desktop TeX editing, follow the host's native editor/compiler workflow when available; use Prism wrappers for template initialization and reproducible strict builds.
