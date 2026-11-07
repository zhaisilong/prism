# Synthetic existing-manuscript case

This small manuscript is a reusable behavioral case for template adaptation.
Every table value, diagram and equation is synthetic. The public FAIR citation
tests bibliography handling and does not support the invented content.

Create a temporary JACS project with Prism, then overlay the files in this
directory. Keep the initialized project's `prism-cjk.sty` and metadata. The
manuscript uses `main.tex`, `si.tex`, a shared local style, section inputs and an
editable TeX figure source. Its own `prism-build.sh` supports `main`, `si` and
`all`; set `PRISM_PROJECT_DIR` to the complete Prism repository when running it.

Use this request for a behavioral check:

> Use paper-latex to adapt this existing bilingual manuscript to Prism's JACS
> drafting template. Improve the figures, tables and captions while preserving
> the manuscript content. Build the main text and supporting information.

Inspect the resulting PDFs at normal reading size and compare the source
content before and after. Run the case only in a temporary directory; generated
PDFs and build artifacts do not belong in this fixture.
