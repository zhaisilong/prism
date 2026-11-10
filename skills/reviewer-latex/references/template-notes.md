# Reviewer Report Template Notes

Use these notes to map an existing review to the maintained parser. Preserve scientific wording and keep editor-only comments separate from author-facing output.

## Metadata

Metadata lines use a recognized Chinese or English label followed by `:` or `：` and a value. Markdown heading markers and common bold label formatting are accepted. English labels are case-insensitive; bilingual labels are also recognized:

| Field | Recognized labels |
| --- | --- |
| Journal | `Journal`, `期刊`, `期刊名称` |
| Header abbreviation | `Journal abbreviation`, `Journal short`, `Journal short name`, `期刊简称`, `期刊缩写` |
| Manuscript/review ID | `Review ID`, `Reviewer ID`, `Review number`, `Manuscript number`, `Manuscript ID`, `MS number`, `稿件编号`, `审稿编号` |
| Title | `Paper title`, `Manuscript title`, `Manuscript`, `Title`, `论文标题`, `稿件标题`, `标题` |
| Recommendation | `Decision`, `Recommendation`, `建议`, `处理建议`, `审稿建议` |

The first non-empty recognized value is used. Explicit command-line metadata options override parsed values. Missing fields retain visible unspecified placeholders; do not invent a journal, title, identifier, or recommendation. `--date` sets the printed date independently of source metadata.

## Heading Aliases

- Overall: `Overall`, `Overall Assessment`, `Overall Comments`, `Summary`, `General Comments`, `Comments to Authors`, `总体评价`, `总体意见`, `给作者的意见`
- Major: `Major`, `Major Concerns`, `Major Comments`, `Major Issues`, `Major Revision Concerns`, `Critical Concerns`, `主要问题`, `主要意见`
- Minor: `Minor`, `Minor Concerns`, `Minor Comments`, `Minor Issues`, `次要问题`, `次要意见`
- Editor only: `Notes`, `Note to Editor`, `Notes to Editor`, `Confidential Comments`, `Confidential Comments to Editor`, `Editor Notes`, `给编辑的保密意见`, `致编辑保密意见`

Matching ignores common heading markers and punctuation, and also supports singular comment/concern/issue variants and mixed Chinese-English headings. An ordinary unrecognized heading remains in the current section; check its placement before delivery. Unrecognized confidential/editor-only labels or ambiguous confidential metadata stop export. Clarify their intended audience before changing such labels. In particular, a section titled `Notes` is confidential editor material.

Major and Minor point numbers are continuous. Editor-only comments are excluded from the author-facing report and written to a separate `_editor_notes` artifact.

## Outputs

The default output directory is the input directory. `--outdir` selects a different final output directory; `--out` overrides the author-facing output path. Companion editor notes use that output's stem plus `_editor_notes`.

For PDF input, the default author-facing filename adds `_review` to preserve the source PDF. `--no-compile` writes persistent TeX instead of PDFs without requiring a compiler; an explicit `--out` path has its suffix changed to `.tex` in this mode. Use `--basename` when a portable output name is needed; it accepts letters, digits, dots, underscores, and hyphens, beginning with a letter or digit.

## Style

The current template uses one accent color, clear metadata, and unnumbered section headings. PDF builds use XeLaTeX or LuaLaTeX with TeX Gyre fonts, plus Fandol and the selected engine's CJK package when Chinese text is present. DOCX input requires `python-docx`; text-based PDF input requires `pypdf` or `pdftotext`. These input dependencies also apply to TeX-only conversion.
