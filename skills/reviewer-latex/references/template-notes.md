# Reviewer Report Template Notes

Use these notes to map an existing review to the maintained parser. Preserve scientific wording and keep editor-only comments separate from author-facing output.

## Metadata

Metadata lines use an English label followed by `:` and a value. Markdown heading markers and common bold label formatting are accepted. Labels are case-insensitive:

| Field | Recognized labels |
| --- | --- |
| Journal | `Journal` |
| Header abbreviation | `Journal abbreviation`, `Journal short`, `Journal short name` |
| Manuscript/review ID | `Review ID`, `Reviewer ID`, `Review number`, `Manuscript number`, `Manuscript ID`, `MS number` |
| Title | `Paper title`, `Manuscript title`, `Manuscript`, `Title` |
| Recommendation | `Decision`, `Recommendation` |

The first non-empty recognized value is used. Explicit command-line metadata options override parsed values. Missing fields retain visible unspecified placeholders; do not invent a journal, title, identifier, or recommendation. `--date` sets the printed date independently of source metadata.

## Heading Aliases

- Overall: `Overall`, `Overall Assessment`, `Overall Comments`, `Summary`, `General Comments`, `Comments to Authors`
- Major: `Major`, `Major Concerns`, `Major Comments`, `Major Issues`, `Major Revision Concerns`, `Critical Concerns`
- Minor: `Minor`, `Minor Concerns`, `Minor Comments`, `Minor Issues`
- Editor only: `Notes`, `Note to Editor`, `Notes to Editor`, `Confidential Comments`, `Confidential Comments to Editor`, `Editor Notes`

Matching is case-insensitive, ignores common heading markers and punctuation, and also supports the singular comment/concern/issue variants in the parser. These are English heading aliases even when the review body contains Chinese. An unrecognized heading stays in the current section; check ambiguous labels in a working copy before exporting. In particular, a section titled `Notes` is treated as confidential editor material.

Major and Minor point numbers are continuous. Editor-only comments are excluded from the author-facing report and written to a separate `_editor_notes` artifact.

## Outputs

The default output directory is the input directory. `--outdir` selects a different final output directory; `--out` overrides the author-facing output path. Companion editor notes use that output's stem plus `_editor_notes`.

For PDF input, the default author-facing filename adds `_review` to preserve the source PDF. `--no-compile` writes persistent TeX instead of PDFs without requiring a compiler; an explicit `--out` path has its suffix changed to `.tex` in this mode. Use `--basename` when a portable output name is needed; it accepts letters, digits, dots, underscores, and hyphens, beginning with a letter or digit.

## Style

The current template uses one accent color, clear metadata, and unnumbered section headings. PDF builds use XeLaTeX or LuaLaTeX with TeX Gyre fonts, plus Fandol and the selected engine's CJK package when Chinese text is present. DOCX input requires `python-docx`; text-based PDF input requires `pypdf` or `pdftotext`. These input dependencies also apply to TeX-only conversion.
