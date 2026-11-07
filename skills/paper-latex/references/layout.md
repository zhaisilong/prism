# Manuscript presentation

Read this when adapting an existing manuscript or changing typography, tables, or figures. Follow the user's selected template and article type. Its class, maintained supporting style, and starter examples define the layout; project-local overrides must be checked against them. Prism's generic styling is described separately below.

## Establish the target and scope

- Read project metadata, the actual document class, preamble, included styles, and rebuild entrypoint. Identify the main text, supplementary material, bibliography, figures, and cross-document references before editing. Existing supplements may be named `si.tex` or use other filenames.
- Compare with a fresh temporary initialization of the same template, article type, and language mode. A metadata/class mismatch needs an established target before replacing the class; do not reinitialize an existing manuscript to migrate its formatting.
- When the request is to conform to a target template, actively correct confirmed inherited conflicts. Preserve scientific wording, values, precision, units, missing-value notation, labels, citation keys, and panel identities. Keep intentional semantic settings such as S numbering. For preview-only work, copy required sources and assets into a temporary project and leave the originals and published PDFs intact.
- Retain the project's engine and bilingual setup unless the requested template requires a change. Chinese support supplements Chinese fonts while retaining the template's Latin and mathematical typography; it does not translate text.

## Correct inherited overrides

Inspect both shared styles and local environments for font family/size, line spacing, page geometry, caption settings, table spacing, fixed dimensions, manual breaks, and float-placement overrides. A local support style can affect every display even when individual figures look clean in the source.

Adjust only settings that conflict with the chosen template or make the output unreadable. Do not globally delete `\small`, `\footnotesize`, `\tabcolsep`, or all local lengths: some maintained starters use them deliberately. Distinguish caption settings from table-body settings and image-internal typography. Prefer a small, scoped correction to layering another global style over the manuscript. Keep upstream class files unchanged; use the maintained Prism derivative or an appropriate project-local adjustment.

## Tables

- Restore the target template's caption and table-body styling before optimizing density. Follow its caption placement and place `\label` after the caption. Use the template's own table macros where supplied; Prism-specific macros are not portable to every journal.
- Size to the current `\linewidth`, accounting for single-column, two-column, and nested environments. Wrap text columns and long headers before reducing font size. Use `tabularx` or explicit column widths when supported; retain consistent units and meaningful row grouping.
- Align numerical values and uncertainty with `siunitx` where compatible. Set `table-format` for the actual digit range, retaining the original precision and missing-value convention. For example, `S[table-format=1.3(3)]` accepts `0.385 +- 0.006`.
- If a table remains too wide, use a template-supported spanning `table*`, split related panels, or arrange an appropriate landscape page. Preserve content and keep panel styles consistent. Do not make whole-table scaling or tiny text the default remedy.
- Use `longtable` with repeated headers and continuation text for multipage tables where the template supports it, typically in a single-column supplement. Do not put it inside a float. Keep table notes at the template's intended size and width.

## Figures and captions

- Prefer vector PDF for plots and diagrams. Retain suitable raster originals and check their effective resolution at the final size. Do not rasterize vectors or stretch the image to fit.
- Replace inherited absolute dimensions with a deliberate width relative to the current `\linewidth` when appropriate. Bound height with `keepaspectratio` when necessary; reserve space for the full caption, caption gap, and surrounding template spacing. A fixed fraction of `\textheight` alone cannot accommodate every long legend.
- Preserve the caption's scientific content and panel identities. Keep its placement, font, and spacing consistent with the target template. Use the template's supported multipanel layout and keep related panels aligned at readable sizes.
- Inspect axis labels, legends, units, annotations, and panel labels at the final PDF size. Their embedded fonts do not change when LaTeX fonts change. If editable plotting sources are available within the authorized project, adjust presentation and re-export while preserving data, calculations, scales, and labels. Inspect the new image. Do not recreate data or paint over a flattened figure to imitate a font change.
- Without editable sources, try a larger display width, a template-supported spanning `figure*`, or a different panel arrangement without cropping content. Report any remaining readability limit rather than claiming it was fixed by caption changes.
- Start with the target template's normal float behavior. Remove inherited forced placement or manual spacing only when it causes a demonstrated problem; inspect placement near first references and avoid large unexplained gaps.

## Equations, supplements, and project builds

- Use `align` for related equalities, `split` inside `equation` for one numbered multiline expression, and `subequations` for a numbered group. Preserve mathematical meaning, symbols, labels, and reference targets while fitting the available column width.
- Most starters provide an independent `supplementary.tex` with S-prefixed counters and its own bibliography. Science Advances instead combines its supplement with the main manuscript. Keep the chosen template's structure and an existing project's actual filenames.
- Build an independent starter supplement with `--main supplementary.tex --no-build-script`; use the same option for `examples.tex` or a separate graphical abstract. This preserves the main rebuild entrypoint. Existing projects with shared references or custom `all/main/si` steps must keep those steps: a single-target wrapper call can bypass reference-map generation. Verify cross-document references against real compiler output.
- Nature defaults to a Prism-maintained `article` draft. Existing or explicitly imported `sn-jnl` projects retain their class typography and project engine; do not add `prism-paper.sty`. These drafts do not replace journal-specific final-file preparation.

## Generic Prism template only

For `--template prism`, `prism-paper.sty` is the reusable presentation layer. Its A4, 11 pt starter uses TeX Gyre Termes text and mathematics, Heros table/caption text, and Fandol Chinese fonts with XeLaTeX or LuaLaTeX. Captions use 9.5/12.5 pt, table cells 9.5/12 pt, and table notes 8.5 pt. These settings are independent of body line spacing and are not defaults for journal templates.

Generic tables inherit `\paperTableStyle`; `Y` and `P{width}` provide text columns, and `\paperTableNote` and `\paperPanelTitle` handle notes and panels. Its results section demonstrates top-aligned subfigures and `\paperFigurePlaceholder`. Its independent `examples.tex` includes repeated-header longtables, a landscape numerical table, and equation examples. Copy only compatible environments when using another template; do not inject the whole generic style. All demonstration data and graphics are synthetic, and example citations should remain only when relevant.

## Verification and delivery

Use the existing project build workflow with strict checks, or `scripts/latex-paper.sh PAPER_DIR --strict --no-build-script` for a simple temporary project. A successful strict build checks missing glyphs, unresolved references, and significant horizontal overflow; it cannot prove template conformity or image readability.

Compare the PDF with the same-template sample at normal reading scale: check the first page, densest tables and figures, long captions, references, multipage table headers, and representative page transitions. Check both main and supplementary material without mechanically imposing main-text typography on the supplement. Exercise the affected engine and language modes after font changes, and confirm sources contain no newly generated build intermediates. Recheck scientific text, numerical values, citation keys, panel identities, and reference resolution after the edits.

Deliver the PDF and actual rebuild command, summarize the formatting changes and any remaining figure-source limitation, and keep private reports, filenames, and research-derived examples out of public documentation or release assets.
