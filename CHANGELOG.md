# Changelog

Record substantive changes under `Unreleased`; move completed entries into a date-version section matching `VERSION`. Historical hyphenated dates describe earlier local maintenance and remain unchanged.

## Unreleased

## 2026.10.27.1

### Added

- Added a JCIM research-paper starter with independent supplementary material, a TOC graphic placeholder, and ACS BibTeX support.

### Changed

- Isolated JCIM builds from same-named source bibliography control files and documented the offline workflow.

### Validation

- Passed all 67 tests, the three wrapper help checks, the paper skill validator, and the JCIM dependency check.
- Strictly compiled and visually checked the JCIM manuscript, supplementary material, and shared examples; verified citation order, conflicting control-file isolation, and failure preservation.
- Audited the public code export; research data, archives, and original local Git history remain outside the snapshot.

## 2026.10.27

### Added

- Added a Drug Discovery Today (`ddt`) narrative-review starter using the installed Elsevier `elsarticle` class, with an independent supplement and optional highlights and teaser placeholders.

### Changed

- Registered the offline DDT template and its pdfLaTeX/BibTeX dependencies without modifying the existing journal templates.
- Kept the concise guide current and excluded Elsevier `.spl` build intermediates from code exports.

### Validation

- Passed all 63 regression tests, three wrapper help checks, the paper skill validator, and the DDT dependency check.
- Strictly compiled and visually checked DDT main, supplementary, and shared examples PDFs; verified numeric superscript references in first-citation order.
- Confirmed offline initialization, failed-build output preservation, main rebuild-script preservation, and source-directory cleanliness including `.spl` files.
- Audited the public code export; research data, archives, and the original local Git history remain outside the public snapshot.

## 2026.10.24.2

### Added

- Added a Briefings in Bioinformatics (`bib`) manuscript starter using the official OUP template, with supplementary material, figures, tables, equations, and numeric BibTeX citations.
- Reused verified official-package import, offline initialization, and project-specific dependency checks for the new journal starter.

### Changed

- Matched the current OUP class's default numeric citation mode and used plain draft page headers, keeping the downloaded class unchanged.
- Kept long supporting tables in an independent single-column supplement and retained the short three-step guide.

### Validation

- Passed all 58 regression tests, paper skill validation, and wrapper help/version checks.
- Strictly compiled BIB main, supplementary, and shared examples PDFs, checked representative pages, and verified actual numeric citation labels and first-appearance order.
- Confirmed source-directory cleanliness, main rebuild-script preservation, the existing Nature template's real strict build, and the public-code export audit.

## 2026.10.24.1

### Changed

- Simplified the README and Chinese guide to template selection, editing, and compilation, with a direct Codex request and two essential commands.
- Moved detailed usage and troubleshooting to an optional reference; build behavior is unchanged.

### Validation

- Checked documentation links, date-version output, and the public-code export audit.

## 2026.10.24

### Added

- Added date versions from a single root `VERSION`, exposed by all three wrapper commands without requiring TeX.
- Added selectable Prism and Nature manuscript starters, independent supplementary material, and synthetic examples for multi-panel figures, dense tables, and equations.
- Added verified import of a pinned official Springer Nature template package, with offline ZIP support and project-specific engine/dependency checks.
- Added a Chinese quick start, usage guide, template source catalog, and public synchronization guide.
- Added audited public-code exports with a file allowlist, content checks, copy verification, and independent Git history for remote synchronization.

### Changed

- Preserved existing Prism manuscript typography while keeping official Nature typography separate; corrected desktop multi-file compilation guidance.
- Kept research data, historical material, third-party template downloads, and the original local Git history outside the public code snapshot.

### Fixed

- Reject paper PDF output paths that resolve to source files, including symbolic-link aliases, before invoking a compiler.
- Reject incompatible engines for registered templates and check the BibTeX executable for manuscript builds.

### Validation

- Passed all 51 regression tests, three skill validators, and all wrapper help, version, and dependency checks.
- Strictly compiled both starters' main documents, supplementary files, and rich examples; inspected title pages, figures, equations, numerical tables, landscape layout, and cross-page headers. Prism also passed LuaLaTeX with an isolated writable font cache.
- Strict note/review fixture builds passed; verified confidential text only appears in the editor output, supplementary builds preserve the main rebuild script, and source directories contain no compilation intermediates.
- Audited the 58-file public code snapshot with SHA-256 inventories; retained research, official downloads, and original Git objects only in local storage.

## 2026-10-10

### Changed

- Applied the shared manuscript typography to an active manuscript and its supplementary information; standardized table headings, captions, title layout, and PDF navigation while preserving scientific content and identifiers.
- Added landscape layouts for the two widest supplementary comparisons and wrapped other crowded tables at a readable font size. Both documents rebuild from one project root with shared style and bibliography resources.

### Validation

- Passed strict XeLaTeX builds for both documents, checked all 44 tables against their original cells and captions, and reviewed title pages, dense tables, figure pages, and pagination. Saved verified pre-change TeX/PDF snapshots and confirmed bibliography and figure files were unchanged.

## 2026-10-09

### Changed

- Added a reusable manuscript style with matched text/math and Chinese fonts, consistent table/caption typography, and controlled figure spacing.
- Added numeric uncertainty alignment, multi-panel figure, and repeating-header longtable examples; documented how to adapt existing manuscripts without changing scientific content.
- Extended the paper dependency check for the presentation packages and math font.

### Validation

- Passed all 19 regression tests, wrapper help checks, and paper dependency checks for both engines.
- Strict XeLaTeX builds and rendered-page checks passed for the template and a copied manuscript; LuaLaTeX passed mixed-language font and multi-page table checks with repeating headers. Verified that the reference manuscript, bibliography, original PDF, build script, and copied figures remained unchanged.

## 2026-09-30

### Changed

- Archived three additional manuscript projects after copy and hash verification, preserving all files and recording their migration manifests.
- Focused Prism on local workflows; retired plugin installation, independent skill distribution, and release packaging to ignored archives.
- Consolidated research material under Notes, Papers, Reviews, and External. Imported historical reviews by journal and manuscript with verified file hashes; preserved historical file contents and archived the Scientific Reports collection.
- Added ignored dated archives, migration manifests, pre-change snapshots, and backups of repaired project entrypoints. Root bibliography ignore rules no longer affect maintained template resources.
- Consolidated build helpers into one local implementation with compatibility shims; rebuild scripts discover the local Prism repository.
- Simplified skill instructions and made the paper initialization template general-purpose while preserving the previous resource-paper template.

### Fixed

- Review TeX-only export now persists author/editor sources without requiring an installed compiler.
- Review output directories now control final artifacts; explicit output paths take precedence and compilation remains isolated in temporary directories.
- Both review PDFs pass compilation and strict checks before existing outputs are updated. Rendering failures clean temporary work directories.
- Dependency checks report missing tools, packages, and fonts together; notes support local bibliography search paths.
- Repaired local project build-script and documented wrapper paths after migration without rebuilding research PDFs.

### Validation

- Added CLI and rebuild regression coverage for confidentiality, output locations, missing dependencies, failed builds, and local project discovery.
- Passed all 19 regression tests and all three wrapper help/dependency checks. Strict fixture builds and rendered-page inspection passed for mixed-language notes, author/editor review outputs, and the general paper template.
- Verified all 136 historical review files byte-for-byte, confirmed the original review directory was retired, and checked that research data and archives remain untracked.
