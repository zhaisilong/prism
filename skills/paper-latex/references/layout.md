# Manuscript presentation

Read this when changing typography, tables, or figures. The template's `prism-paper.sty` is the reusable presentation layer; `main.tex` controls the document class, page geometry, title, and manuscript structure.

## Typography

- Use A4 and an 11 pt body as the default manuscript layout. Journal requirements can override these defaults.
- The style matches TeX Gyre Termes text and mathematics, uses Heros for table/caption text, and Fandol Song/Hei for Chinese. Fonts ship with the TeX distribution and work with XeLaTeX or LuaLaTeX.
- Captions use 9.5 pt text with 12.5 pt leading; table cells use 9.5 pt with 12 pt leading. These settings are independent of the body's line spacing. Table notes use 8.5 pt.
- Apply a style to an existing manuscript only within the user's scope. To demonstrate a proposed layout, copy the source, bibliography, and required figures into a temporary project, then load `prism-paper.sty` there.

## Tables

- Put the caption and its `\label` above the table. Use `\toprule`, `\midrule`, and `\bottomrule`; avoid vertical rules.
- Ordinary table floats inherit `\paperTableStyle`. Remove old local `\footnotesize`/`\tabcolsep` overrides when deliberately adopting the new defaults.
- Use `tabularx` with `Y` for wrapping text and `P{width}` when a fixed text width is needed. Put long units or dataset sizes on a second header line with `\shortstack{...\\...}`.
- Use `siunitx` `S` columns for numeric alignment, specifying `table-format` for the actual digit range. For example, `S[table-format=1.3(3)]` accepts uncertainty input such as `0.385 +- 0.006`; the template results section shows this in context. Preserve the source precision and missing-value convention.
- Place explanations below the cells with `\paperTableNote{...}`. Use `\paperPanelTitle{(a) ...}` for related blocks within one table, keeping all panels at the same font size and width.
- For tables spanning pages, use the appendix's `longtable` example with repeated column headers and continuation text. Do not put a `longtable` inside a float.
- Fix crowded tables by wrapping headers/text, selecting sensible column widths, or splitting panels. Do not shrink an entire table with `\resizebox` as the first remedy; check legibility at normal PDF viewing size.

The independent `examples.tex` contains a longtable with enough synthetic rows to cross a page boundary, and a dedicated landscape page for a wide numerical table. Compile it with `--main examples.tex --no-build-script`; copy only the required environment into the manuscript.

## Figures

- Prefer vector PDF for plots and diagrams; retain raster images when the source warrants them. Use `width=\linewidth` or a deliberate fraction of it and `keepaspectratio` when both dimensions are bounded.
- Account for long legends when setting figure height. A typical bound is `height=0.62\textheight`, with `width=\linewidth,keepaspectratio`; inspect the final labels rather than applying this bound blindly.
- Keep the caption below the image. Preserve its scientific content and existing panel identities. Explain symbols, units, uncertainty, and sample sizes where the manuscript already supplies them.
- The results section demonstrates two top-aligned `subfigure` panels. Replace `\paperFigurePlaceholder` with the real `\includegraphics` call; the placeholders are layout examples, not study results.
- Axis/legend fonts embedded in PDF/PNG graphics cannot be changed by the LaTeX body font. If they are too small at the final size, use the original plotting source when available and authorized, or enlarge/rearrange the figure.
- Allow normal `[htbp]` placement. The style controls float spacing and aligns float pages at the top; inspect figure placement near its first reference.

## Equations and supplementary material

- Use `align` for related equalities, `split` within `equation` for a single numbered multi-line expression, and `subequations` for a related group. `examples.tex` demonstrates `cases`, matrices, and references to both a group and individual equations. Define the symbols and assumptions before adopting any expression.
- `supplementary.tex` is a separate document with independent S-prefixed figure, table and equation counters and its own bibliography. Build it with `--main supplementary.tex --no-build-script`; do not include it in `main.tex` or rely on the main manuscript's auxiliary files.
- Every illustrative number and graphic is synthetic. Remove or replace the demonstrations before delivery. The public demonstration citation exercises bibliography mechanics and must be retained only if it is relevant to the study.
- The optional Nature starter uses `sn-jnl` with `sn-nature` and pdfLaTeX, without `prism-paper.sty` or replacement fonts. Keep its class typography intact. Its single-file manuscript is an initial drafting aid; journal-specific final-file preparation remains a separate task.

## Verification

Compile a temporary manuscript with `scripts/latex-paper.sh PAPER_DIR --strict --no-build-script`. Check the title page, dense numeric tables, long captions, and longtable continuation pages at normal scale. Exercise both supported engines after changing font configuration. Keep research source files and published PDFs intact when they are only references for the task.
