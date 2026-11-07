---
name: paper-latex
description: Initialize academic LaTeX manuscripts, adapt existing manuscript layouts to Prism journal templates, or compile papers with bibliography and supplementary material. Use for manuscript projects; route ordinary single-file notes to notes-latex.
---

# Paper LaTeX

Use the complete Prism repository as the source of truth. Run its root wrapper by absolute path when outside the repository; the installed skill is only an entrypoint. Respect `PRISM_PROJECT_DIR` when the repository has moved. Never fall back to an older installed copy of the build implementation.

## Create and build

```bash
scripts/latex-templates.sh
scripts/latex-paper.sh --init TARGET_DIR --template TEMPLATE
scripts/latex-paper.sh TARGET_DIR --strict
```

Default starters initialize offline and support mixed Chinese and English. Journal starters use XeLaTeX; generic Prism also supports LuaLaTeX. At initialization, `--language english` selects a journal's pdfLaTeX mode; it does not translate text. Bibliography entries remain English. Choose templates and article types from the catalog. Read [template sources](../../docs/templates.md) for journal structure, citations, and licensing, or the [short Chinese guide](../../docs/guide.zh-CN.md) for user instructions.

- For an existing manuscript, read [layout guidance](references/layout.md) before adapting presentation. Identify its target template, class, local styles, and actual build entrypoint. When asked to match that template, proactively correct confirmed conflicting legacy formatting within the requested scope; preserve scientific content, numerical precision, units, citation keys, and panel identities.
- Keep existing project structure and cross-document build steps. Use a temporary copy when only a preview is requested. Replace demonstration text, authors, and citations before delivery; do not invent scientific claims, data, or references.
- Preserve the main `prism-build.sh` when compiling independent supplements or examples: use `--main supplementary.tex --no-build-script` or `--main examples.tex --no-build-script`. Science Advances combines its supplement with the main text.
- Inspect the first page, references, dense figures/tables, long captions, and representative pagination against the selected template at normal reading scale. Strict compilation checks do not establish template conformity; check embedded figure text separately.
- Link the final PDF and give the actual rebuild command, including any project-specific target. Builds use temporary directories and preserve the previous PDF on failure. Use `--keep-work` only for debugging and report the retained path.

## Options and boundaries

- `--check-deps` checks the initialized project's engine and resources; `--version` needs no TeX. Missing dependencies should be reported, not silently installed.
- Initialization refuses a nonempty directory unless explicitly requested with `--force`, which backs it up. Preserve unrelated build scripts unless `--force-build-script` is requested.
- Nature defaults to a Prism-maintained `article` draft. Existing `sn-jnl` projects remain supported; explicit local official import uses `--template-source`. Read [advanced usage](../../docs/reference.zh-CN.md) only when needed.
- NAR and Angew offer multiple `--article-type` values at initialization. Read the [NAR](../../docs/templates.md#nar) or [Angew](../../docs/templates.md#angew) notes for proposal requirements and special content. Separate graphical abstracts use `--no-build-script`; Angew's TOC entry is on the main text's last page.
- Existing projects keep their engine and language mode unless a change is requested or required by the chosen template. For bilingual conversion, follow the documented manual setup with an explicit engine. Preserve unrelated rebuild scripts.
- Install or update the local entrypoint only when requested, using `scripts/install-paper-skill.py`. Do not copy the shared implementation into global skills or modify other skills.
- Keep research files and local installation paths private. Do not submit manuscripts, publish research, or upload project contents as part of formatting.
- Route single-file notes to `notes-latex` and existing peer-review drafts to `reviewer-latex`. Do not convert a Markdown, DOCX, or PDF document into a complete scientific paper.

For desktop TeX editing, follow the host's native editor/compiler workflow when available; use Prism wrappers for template initialization and reproducible strict builds.
