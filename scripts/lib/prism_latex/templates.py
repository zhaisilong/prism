"""Small, pinned template catalog and safe manuscript initialization."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import TypedDict

from .build_support import project_version


PROJECT_DIR = Path(__file__).resolve().parents[3]
ASSET_DIR = PROJECT_DIR / "skills" / "paper-latex" / "assets"
METADATA_NAME = "prism-template.json"
BUNDLED_PACKAGES = {
    "oup": ("1.5", "oup/1.5"), "science": ("1.0", "science/1.0"),
    "wiley-overleaf": ("1.5", "wiley-overleaf/2019"),
}
BUNDLED_NOTICES = {
    "oup": {"README": "oup-template-README", "manifest.txt": "oup-template-manifest.txt",
            "NOTICE.md": "oup-template-NOTICE.md", "LICENSE.txt": "oup-template-LICENSE.txt"},
    "science": {"NOTICE.md": "science-template-NOTICE.md", "LICENSE.txt": "science-template-LICENSE.txt"},
    "wiley-overleaf": {"NOTICE.md": "wiley-template-NOTICE.md", "LICENSE.txt": "wiley-template-LICENSE.txt"},
}
NATURE_URL = "https://cms-resources.apps.public.k8s.springernature.io/springer-cms/rest/v1/content/18782940/data/v12"
NATURE_SIZE = 901814
NATURE_SHA256 = "812e76dcaa9c28dc1bff1fb6065d51729b67d4ea140552a05088317414a3ecae"
NATURE_ARCHIVE = "springer-nature-latex-template.zip"
NATURE_MEMBERS = {
    "sn-article-template/sn-jnl.cls": "sn-jnl.cls",
    "sn-article-template/bst/sn-nature.bst": "sn-nature.bst",
}
BIB_URL = "https://mirrors.ctan.org/macros/latex/contrib/oup-authoring-template.zip"
BIB_SIZE = 257751
BIB_SHA256 = "025434f53ed3a46b9fd84d50a78c734c309476bc47b1cb7a90c383734df38e97"
BIB_ARCHIVE = "oup-authoring-template.zip"
BIB_MEMBERS = {
    "oup-authoring-template/oup-authoring-template.cls": "oup-authoring-template.cls",
    "oup-authoring-template/oup-plain.bst": "oup-plain.bst",
}
BIOINFORMATICS_MEMBERS = {
    "oup-authoring-template/oup-authoring-template.cls": "oup-authoring-template.cls",
    "oup-authoring-template/oup-abbrvnat.bst": "oup-abbrvnat.bst",
}
# Science-family v1.0 (July 2024), verified against the user-supplied
# publisher package. Individual hashes also permit a ZIP to be repacked.
SCIENCE_SHA256 = {
    "scicite.sty": "8030d7867d4094da12e59f3f0a6bc1d646d9c8454518872086d34bf25bbf2a99",
    "sciencemag.bst": "2ce0f9f1dad69ab331fbf1a8d0210d757f85043025f777ba01e53533c3b659c3",
    "readme.txt": "a8ede7d50779a9f5e82f332780efeba5b6dba4b9cc04c87b1d0fd2464cc1cd9d",
}
SCIENCE_MEMBERS = {
    "scicite.sty": "scicite.sty",
    "sciencemag.bst": "sciencemag.bst",
    "readme.txt": "science-template-readme.txt",
}
class TemplateRecord(TypedDict, total=False):
    """Catalog data; conference identity and rendering stages stay separate."""

    id: str
    kind: str
    venue: str
    publisher: str | None
    article_type: str
    article_types: tuple[str, ...]
    backend: str
    directory: str
    engine: str
    description: str
    # Reserved for concrete, verified conference profiles. These never imply
    # a blind-review policy or a rendering mode for another edition or track.
    edition: int
    track: str
    stage: str


# The short keys remain compatibility aliases. IDs name a venue, while the
# backend describes reusable build and import behavior.
TEMPLATES: dict[str, TemplateRecord] = {
    "prism": {
        "id": "generic/prism", "kind": "generic", "venue": "Prism",
        "publisher": None, "article_type": "manuscript", "backend": "prism",
        "directory": "paper-template",
        "engine": "auto",
        "description": "Prism manuscript; English / Chinese; XeLaTeX or LuaLaTeX (default)",
    },
    "nature": {
        "id": "family/nature-nmi", "kind": "family", "venue": "Nature / NMI draft",
        "publisher": "Springer Nature", "article_type": "research", "backend": "nature",
        "directory": "nature-template",
        "engine": "pdflatex",
        "description": "Nature / NMI manuscript and supplementary information; bilingual / English",
    },
    "nature-communications": {
        "id": "journal/nature-communications", "kind": "journal", "venue": "Nature Communications",
        "publisher": "Springer Nature", "article_type": "research", "backend": "nature-communications",
        "directory": "nature-communications-template",
        "engine": "pdflatex",
        "description": "Nature Communications research article and supplementary information; bilingual / English",
    },
    "jcheminformatics": {
        "id": "journal/journal-of-cheminformatics", "kind": "journal",
        "venue": "Journal of Cheminformatics", "publisher": "Springer Nature",
        "article_type": "research", "backend": "jcheminformatics",
        "directory": "jcheminformatics-template", "engine": "pdflatex",
        "description": "Journal of Cheminformatics research article and supplementary information; bilingual / English",
    },
    "science-advances": {
        "id": "journal/science-advances", "kind": "journal", "venue": "Science Advances",
        "publisher": "AAAS", "article_type": "research", "backend": "science",
        "directory": "science-advances-template",
        "engine": "pdflatex",
        "description": "Science Advances research article and combined supplementary material; bilingual / English",
    },
    "bib": {
        "id": "journal/briefings-in-bioinformatics", "kind": "journal", "venue": "Briefings in Bioinformatics",
        "publisher": "Oxford University Press", "article_type": "manuscript", "backend": "oup-numeric",
        "directory": "bib-template",
        "engine": "pdflatex",
        "description": "Briefings in Bioinformatics (OUP); bilingual / English",
    },
    "ddt": {
        "id": "journal/drug-discovery-today", "kind": "journal", "venue": "Drug Discovery Today",
        "publisher": "Elsevier", "article_type": "review", "backend": "ddt",
        "directory": "ddt-template",
        "engine": "pdflatex",
        "description": "Drug Discovery Today narrative review (Elsevier); bilingual / English",
    },
    "jcim": {
        "id": "journal/jcim", "kind": "journal", "venue": "Journal of Chemical Information and Modeling",
        "publisher": "ACS", "article_type": "research", "backend": "acs",
        "directory": "jcim-template",
        "engine": "pdflatex",
        "description": "Journal of Chemical Information and Modeling research article (ACS); bilingual / English",
    },
    "jacs": {
        "id": "journal/jacs", "kind": "journal", "venue": "Journal of the American Chemical Society",
        "publisher": "ACS", "article_type": "research", "backend": "acs",
        "directory": "jacs-template", "engine": "pdflatex",
        "description": "Journal of the American Chemical Society research article (ACS); bilingual / English",
    },
    "bioinformatics": {
        "id": "journal/bioinformatics", "kind": "journal", "venue": "Bioinformatics",
        "publisher": "Oxford University Press", "article_type": "original", "backend": "oup-authoryear",
        "directory": "bioinformatics-template", "engine": "pdflatex",
        "description": "Bioinformatics original paper (OUP); bilingual / English",
    },
    "nar": {
        "id": "journal/nucleic-acids-research", "kind": "journal", "venue": "Nucleic Acids Research",
        "publisher": "Oxford University Press", "article_type": "research",
        "article_types": ("research", "database", "web-server"), "backend": "oup-nar",
        "directory": "nar-template", "engine": "pdflatex",
        "description": "NAR research, Database and Web Server manuscripts (OUP Modern Large); bilingual / English",
    },
    "angew": {
        "id": "journal/angewandte-chemie-international-edition", "kind": "journal",
        "venue": "Angewandte Chemie International Edition", "publisher": "Wiley-VCH",
        "article_type": "research", "article_types": ("research", "communication", "review", "minireview"),
        "backend": "wiley-overleaf", "directory": "angew-template", "engine": "pdflatex",
        "description": "Angew research, communication, review and minireview drafts; Prism-maintained Wiley derivative; bilingual / English",
    },
}
PRISM_PACKAGES = (
    "iftex.sty", "bookmark.sty", "graphicx.sty", "caption.sty",
    "unicode-math.sty", "texgyretermes-math.otf", "subcaption.sty",
    "siunitx.sty", "ragged2e.sty", "etoolbox.sty", "xurl.sty",
    "enumitem.sty", "booktabs.sty", "tabularx.sty", "longtable.sty",
    "amsmath.sty", "amssymb.sty", "natbib.sty", "fancyhdr.sty", "pdflscape.sty",
)
NATURE_PACKAGES = (
    "graphicx.sty", "amsmath.sty", "amssymb.sty", "amsfonts.sty",
    "booktabs.sty", "tabularx.sty", "siunitx.sty", "longtable.sty",
    "setspace.sty", "cuted.sty", "rotating.sty", "threeparttable.sty",
    "appendix.sty", "wrapfig.sty", "amsthm.sty", "fix-cm.sty", "natbib.sty",
    "caption.sty", "subcaption.sty", "pdflscape.sty",
)
NATURE_COMMUNICATIONS_PACKAGES = (
    "article.cls", "geometry.sty", "hyperref.sty", "array.sty", "graphicx.sty", "amsmath.sty", "amssymb.sty",
    "booktabs.sty", "tabularx.sty", "siunitx.sty", "longtable.sty",
    "caption.sty", "subcaption.sty", "pdflscape.sty", "natbib.sty", "unsrt.bst",
)
SCIENCE_PACKAGES = (
    "article.cls", "graphicx.sty", "newtxtext.sty", "newtxmath.sty",
    "url.sty", "amsmath.sty", "amssymb.sty", "booktabs.sty",
    "tabularx.sty", "siunitx.sty", "longtable.sty", "caption.sty",
    "subcaption.sty", "pdflscape.sty", "natbib.sty", "unsrtnat.bst",
)
BIB_PACKAGES = (
    "crop.sty", "graphicx.sty", "caption.sty", "amsmath.sty", "array.sty",
    "color.sty", "xcolor.sty", "amssymb.sty", "flushend.sty", "stfloats.sty",
    "rotating.sty", "chngpage.sty", "totcount.sty", "fix-cm.sty", "footmisc.sty",
    "natbib.sty", "wrapfig.sty", "amsthm.sty", "subfloat.sty", "multirow.sty",
    "footnote.sty", "url.sty", "mathrsfs.sty", "algorithm.sty", "algorithmicx.sty",
    "algpseudocode.sty", "listings.sty", "hyperref.sty", "tikz.sty", "booktabs.sty",
    "tabularx.sty", "siunitx.sty", "longtable.sty", "subcaption.sty", "pdflscape.sty",
    "unsrt.bst",
)
DDT_PACKAGES = (
    "elsarticle.cls", "elsarticle-num.bst", "natbib.sty", "graphicx.sty",
    "amsmath.sty", "amssymb.sty", "booktabs.sty", "tabularx.sty",
    "siunitx.sty", "longtable.sty", "caption.sty", "subcaption.sty",
    "pdflscape.sty",
)
JCIM_PACKAGES = (
    "article.cls", "achemso.sty", "achemso.bst", "xkeyval.sty", "natbib.sty",
    "natmove.sty", "graphicx.sty", "amsmath.sty", "amssymb.sty",
    "booktabs.sty", "tabularx.sty", "siunitx.sty", "longtable.sty",
    "caption.sty", "subcaption.sty", "pdflscape.sty",
)
WILEY_PACKAGES = (
    "article.cls", "ifpdf.sty", "ifxetex.sty", "ifluatex.sty", "mathtools.sty", "bm.sty",
    "graphicx.sty", "tabularx.sty", "textcase.sty", "dashrule.sty", "ragged2e.sty",
    "authblk.sty", "url.sty", "soul.sty", "xpatch.sty", "afterpage.sty", "lineno.sty",
    "mdframed.sty", "tikz.sty", "silence.sty", "microtype.sty", "geometry.sty",
    "alphalph.sty", "scrextend.sty", "titlesec.sty", "footmisc.sty", "fancyhdr.sty",
    "changepage.sty", "environ.sty", "marginnote.sty", "quoting.sty", "enumitem.sty",
    "caption.sty", "threeparttable.sty", "stfloats.sty", "newfloat.sty", "enotez.sty",
    "natbib.sty", "lettrine.sty", "hyperref.sty", "booktabs.sty", "longtable.sty",
    "siunitx.sty", "mhchem.sty", "subcaption.sty", "pdflscape.sty", "amssymb.sty",
)


BUILD_PROFILES = {
    "prism": {"packages": PRISM_PACKAGES, "source": None, "examples": False},
    "nature": {"packages": NATURE_COMMUNICATIONS_PACKAGES + ("geometry.sty", "hyperref.sty", "amsfonts.sty", "array.sty"), "source": "nature", "examples": True},
    "nature-communications": {"packages": NATURE_COMMUNICATIONS_PACKAGES, "source": None, "examples": True},
    "jcheminformatics": {"packages": NATURE_COMMUNICATIONS_PACKAGES + ("lineno.sty", "setspace.sty"), "source": None, "examples": True},
    "science": {"packages": SCIENCE_PACKAGES, "source": "science", "examples": True},
    "oup-numeric": {"packages": BIB_PACKAGES, "source": "oup-numeric", "examples": True},
    "oup-authoryear": {"packages": BIB_PACKAGES + ("unsrtnat.bst",), "source": "oup-authoryear", "examples": True},
    "oup-nar": {"packages": BIB_PACKAGES + ("geometry.sty",), "source": "oup-numeric", "examples": True,
                "resources": ("prism-nar.bst",),
                "required_common": ("supplementary.tex", "graphical_abstract.tex", "references.bib", "prism-nar.bst")},
    "wiley-overleaf": {
        "packages": WILEY_PACKAGES, "source": None, "examples": True,
        "bundled": ("wiley-overleaf", {"wiley-article.cls": "wiley-article.cls"}),
        "shared_assets": ("prism-wiley-article.cls",),
        "resources": ("prism-wiley-article.cls", "prism-angew.bst",
                      "wiley-template-NOTICE.md", "wiley-template-LICENSE.txt"),
        "required_common": ("supplementary.tex", "references.bib", "prism-angew.bst", "NOTICE.md"),
    },
    "ddt": {"packages": DDT_PACKAGES, "source": None, "examples": True},
    # achemso writes a job-specific control .bib; BibTeX must run away from
    # source files so that an unrelated same-named file cannot override it.
    "acs": {"packages": JCIM_PACKAGES, "source": None, "examples": True, "isolate_cwd": True},
}


def template_choices() -> tuple[str, ...]:
    """Expose aliases and stable IDs, rejecting an ambiguous registration."""
    names: list[str] = []
    for alias, details in TEMPLATES.items():
        canonical = details["id"]
        kind = details["kind"]
        if kind not in ("generic", "family", "journal", "conference") or not canonical.startswith(f"{kind}/"):
            raise ValueError(f"Invalid Prism template ID or kind: {alias} / {canonical}")
        if alias in names or canonical in names or alias == canonical:
            raise ValueError(f"Duplicate Prism template name: {alias} / {canonical}")
        if details["backend"] not in BUILD_PROFILES:
            raise ValueError(f"Unknown build profile for {alias}: {details['backend']}")
        article_types = details.get("article_types")
        if article_types is not None and (not isinstance(article_types, tuple) or not article_types
                or any(not isinstance(value, str) or not value for value in article_types)
                or len(set(article_types)) != len(article_types) or details["article_type"] not in article_types):
            raise ValueError(f"Invalid article types for {alias}")
        names.extend((alias, canonical))
    return tuple(names)


def resolve_template(name: str) -> str:
    """Resolve a stable ID or legacy alias to its compatibility alias."""
    template_choices()
    for alias, details in TEMPLATES.items():
        if name == alias or name == details["id"]:
            return alias
    raise ValueError(f"unknown template: {name}")


def article_type_choices() -> tuple[str, ...]:
    """CLI choices come only from templates that expose content selection."""
    template_choices()
    return tuple(dict.fromkeys(value for record in TEMPLATES.values()
                               for value in record.get("article_types", ())))


def format_template_catalog(group_by: str = "none") -> str:
    """Render the one registry; retain the original flat command's output."""
    template_choices()
    if group_by == "none":
        rows = []
        for alias, record in TEMPLATES.items():
            publisher = record["publisher"] or "Prism"
            articles = f"; article types: {', '.join(record['article_types'])}" if record.get("article_types") else ""
            rows.append(f"{alias}: {record['description']} [ID: {record['id']}; type: {record['kind']}; publisher: {publisher}{articles}]")
        return "\n".join(rows)
    if group_by != "publisher":
        raise ValueError("Unsupported template grouping; use none or publisher")
    groups: dict[str, list[tuple[str, TemplateRecord]]] = {}
    for alias, record in TEMPLATES.items():
        label = "Prism / 通用" if record["kind"] == "generic" else record["publisher"] or "未指定出版社"
        groups.setdefault(label, []).append((alias, record))
    rows = []
    for label in sorted(groups, key=lambda value: (value != "Prism / 通用", value.casefold())):
        if rows:
            rows.append("")
        rows.append(label)
        for alias, record in sorted(groups[label], key=lambda item: (item[1]["venue"].casefold(), item[0])):
            rows.append(f"  {alias}: {record['venue']} [ID: {record['id']}]")
            if record.get("article_types"):
                options = ", ".join(record["article_types"])
                rows.append(f"    --article-type: {options} (default: {record['article_type']})")
            else:
                rows.append(f"    用途: {record['description']}")
    return "\n".join(rows)


def template_profile(template: str, variant: str | None = None) -> dict:
    alias = resolve_template(template)
    if alias == "nature":
        if variant not in (None, "prism-article", "sn-jnl"):
            raise ValueError("unknown Nature template variant")
        if variant == "sn-jnl":
            return {**BUILD_PROFILES["nature"], "packages": NATURE_PACKAGES}
    elif variant is not None:
        raise ValueError("template variant is only supported for Nature")
    return BUILD_PROFILES[TEMPLATES[alias]["backend"]]


def template_isolated_build(template: str | None) -> bool:
    return bool(template and template_profile(template).get("isolate_cwd", False))


def template_article_type(template: str, requested: str | None = None) -> str:
    """Select content within a venue without changing its rendering variant."""
    record = TEMPLATES[resolve_template(template)]
    if requested is None:
        return record["article_type"]
    if not isinstance(requested, str) or requested not in record.get("article_types", ()):
        raise ValueError(f"Unsupported article type for {template}: use a type listed by --list-templates")
    return requested


def _template_metadata(project: Path) -> tuple[str | None, str | None, str | None, str | None]:
    path = project / METADATA_NAME
    if not path.exists():
        return None, None, None, None
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        template = resolve_template(metadata["template"])
        if "schema_version" in metadata or "template_id" in metadata:
            if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1:
                raise ValueError("unsupported template metadata schema version")
            if metadata.get("template_id") != TEMPLATES[template]["id"]:
                raise ValueError("template and template_id do not match")
        if "variant" in metadata:
            variant = metadata["variant"]
            if template != "nature" or not isinstance(variant, str) or variant not in ("prism-article", "sn-jnl"):
                raise ValueError("invalid template variant")
        else:
            # Nature projects created before offline starters use sn-jnl.
            variant = "sn-jnl" if template == "nature" else None
        language = metadata.get("language")
        if "language" in metadata and language not in ("bilingual", "english"):
            raise ValueError("invalid template language")
        if "article_type" in metadata and metadata["article_type"] is None:
            raise ValueError("invalid article type")
        article_type = template_article_type(template, metadata.get("article_type"))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(f"Invalid Prism template metadata: {path}: {exc}") from exc
    return template, variant, language, article_type


def template_for_project(project: Path) -> str | None:
    return _template_metadata(project)[0]


def template_variant_for_project(project: Path) -> str | None:
    return _template_metadata(project)[1]


def template_language_for_project(project: Path) -> str | None:
    return _template_metadata(project)[2]


def template_article_type_for_project(project: Path) -> str | None:
    return _template_metadata(project)[3]


def template_engine(template: str | None, requested: str, language: str | None = None) -> str:
    if language not in (None, "bilingual", "english"):
        raise SystemExit("Invalid template language; use bilingual or english.")
    alias = resolve_template(template) if template else None
    if alias and TEMPLATES[alias]["backend"] == "prism" and requested == "pdflatex":
        raise SystemExit("The prism template requires XeLaTeX or LuaLaTeX; use --engine auto, xelatex, or lualatex.")
    if alias and TEMPLATES[alias]["engine"] == "pdflatex":
        if language == "bilingual":
            if requested not in ("auto", "xelatex"):
                raise SystemExit(f"The bilingual {alias} template requires XeLaTeX; use --engine auto or xelatex.")
            return "xelatex"
        if requested in ("auto", "pdflatex"):
            return "pdflatex"
        if requested == "xelatex":
            return "xelatex"
        raise SystemExit(f"The {alias} template supports pdfLaTeX or XeLaTeX; use --engine auto, pdflatex, or xelatex.")
    return requested


def template_packages(
    template: str | None, engine: str, variant: str | None = None,
    language: str | None = None,
) -> tuple[str, ...]:
    engine = template_engine(template, engine, language)
    if template:
        profile = template_profile(template, variant)
        packages = profile["packages"]
        if TEMPLATES[resolve_template(template)]["backend"] == "wiley-overleaf":
            if engine == "xelatex":
                packages += ("fontspec.sty", "unicode-math.sty", "texgyretermes-regular.otf", "texgyretermes-bold.otf",
                             "texgyretermes-italic.otf", "texgyretermes-bolditalic.otf",
                             "XITSMath-Regular.otf", "XITSMath-Bold.otf", "Lato-Regular.ttf",
                             "Lato-Bold.ttf", "Lato-Italic.ttf", "Lato-BoldItalic.ttf", "Lato-Black.ttf")
            else:
                packages += ("tgtermes.sty", "lato.sty", "stix.sty")
        return packages
    # Existing, unmarked projects can explicitly request pdfLaTeX too.
    if engine == "pdflatex":
        return ("graphicx.sty", "amsmath.sty", "amssymb.sty", "natbib.sty")
    return PRISM_PACKAGES


def _pinned_package(
    source: Path | None, *, label: str, size: int,
    sha256: str, required: dict[str, str],
) -> tuple[bytes, dict[str, bytes]]:
    """Validate an explicitly supplied original archive; never fetch online."""
    if source is None:
        raise SystemExit(f"The official {label} mode requires --template-source PACKAGE.zip; initialization does not download files.")
    try:
        archive = _read_science_file(source.expanduser(), size)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Cannot read the pinned {label} template package: {exc}. The initialization target was not changed.") from exc
    digest = hashlib.sha256(archive).hexdigest()
    if len(archive) != size or digest != sha256:
        raise SystemExit(f"{label} template package checksum mismatch; expected the pinned official ZIP. The initialization target was not changed.")
    members: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            names = package.namelist()
            for member, destination in required.items():
                if names.count(member) != 1:
                    raise ValueError(f"required member missing or duplicated: {member}")
                info = package.getinfo(member)
                mode = info.external_attr >> 16
                if info.is_dir() or stat.S_ISLNK(mode) or info.file_size > 2_000_000:
                    raise ValueError(f"unsafe required member: {member}")
                members[destination] = package.read(info)
    except (zipfile.BadZipFile, KeyError, ValueError, RuntimeError, OSError) as exc:
        raise SystemExit(f"Invalid {label} template ZIP: {exc}. The initialization target was not changed.") from exc
    return archive, members


def nature_package(source: Path | None) -> tuple[bytes, dict[str, bytes]]:
    return _pinned_package(
        source, label="Nature", size=NATURE_SIZE,
        sha256=NATURE_SHA256, required=NATURE_MEMBERS,
    )


def bib_package(source: Path | None) -> tuple[bytes, dict[str, bytes]]:
    return _pinned_package(
        source, label="BIB", size=BIB_SIZE,
        sha256=BIB_SHA256, required=BIB_MEMBERS,
    )


def bioinformatics_package(source: Path | None) -> tuple[bytes, dict[str, bytes]]:
    return _pinned_package(
        source, label="Bioinformatics", size=BIB_SIZE,
        sha256=BIB_SHA256, required=BIOINFORMATICS_MEMBERS,
    )


def _read_science_file(path: Path, limit: int) -> bytes:
    """Read one bounded regular file without following a final symlink."""
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError(f"not a regular file or too large: {path.name}")
        content = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
        if len(content) > limit or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"file changed during reading or exceeds size limit: {path.name}")
        return content


def science_package(source: Path | None) -> dict[str, bytes]:
    """Read the pinned Science v1.0 files from a user-supplied folder or ZIP.

    Hashes establish reproducibility against this recorded version; they do not
    independently authenticate a user-supplied package's provenance.
    """
    if source is None:
        raise SystemExit("Science Advances initialization requires --template-source with the official Science-family folder or ZIP. The initialization target was not changed.")
    source = source.expanduser()
    try:
        if source.is_symlink():
            raise ValueError("template source must not be a symbolic link")
        if source.is_dir():
            contents = {name: _read_science_file(source / name, 2_000_000) for name in SCIENCE_MEMBERS}
        else:
            archive = _read_science_file(source, 10_000_000)
            contents = {}
            with zipfile.ZipFile(io.BytesIO(archive)) as package:
                entries = package.infolist()
                if len(entries) > 256 or sum(info.file_size for info in entries) > 20_000_000:
                    raise ValueError("ZIP exceeds entry or uncompressed-size limit")
                seen_names = set()
                for info in entries:
                    name = info.filename
                    parts = name.rstrip("/").split("/")
                    if (not name or name.startswith("/") or "\\" in name
                            or any(part in ("", ".", "..") or ":" in part for part in parts)):
                        raise ValueError("ZIP contains an unsafe path")
                    file_type = stat.S_IFMT(info.external_attr >> 16)
                    if file_type not in (0, stat.S_IFREG, stat.S_IFDIR) or info.file_size > 2_000_000:
                        raise ValueError("ZIP contains a link, special file, or oversized member")
                    basename = parts[-1]
                    canonical = next((key for key in SCIENCE_MEMBERS if key.casefold() == basename.casefold()), None)
                    if canonical is None:
                        continue
                    if canonical in seen_names or basename != canonical or info.is_dir():
                        raise ValueError(f"required member is duplicated or has incorrect name: {canonical}")
                    seen_names.add(canonical)
                    contents[canonical] = package.read(info)
            if set(contents) != set(SCIENCE_MEMBERS):
                raise ValueError("ZIP does not contain each required Science style and readme exactly once")
        for name, content in contents.items():
            if hashlib.sha256(content).hexdigest() != SCIENCE_SHA256[name]:
                raise ValueError(f"checksum mismatch for {name}; expected Science-family v1.0")
        return {SCIENCE_MEMBERS[name]: content for name, content in contents.items()}
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise SystemExit(f"Invalid Science-family template source: {exc}. The initialization target was not changed.") from exc


def _bundled_package(package_id: str, required: dict[str, str]) -> tuple[dict[str, bytes], dict]:
    """Verify the maintained source selection before touching a target."""
    root = ASSET_DIR / "upstream"
    version, directory = BUNDLED_PACKAGES[package_id]
    try:
        manifest = json.loads(_read_science_file(root / "manifest.json", 100_000).decode("utf-8"))
        if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
            raise ValueError("unsupported bundled manifest schema")
        packages = [record for record in manifest["packages"] if record["id"] == package_id]
        if len(packages) != 1 or packages[0]["version"] != version:
            raise ValueError("missing, duplicated or unexpected bundled package version")
        package = packages[0]
        files: dict[str, bytes] = {}
        for record in package["files"]:
            relative = Path(record["path"])
            if relative.parent.as_posix() != directory or relative.name in files:
                raise ValueError("unsafe or duplicated bundled member")
            size = record["size"]
            if type(size) is not int or not 0 <= size <= 2_000_000:
                raise ValueError("invalid bundled member size")
            content = _read_science_file(root / relative, size)
            if len(content) != size or hashlib.sha256(content).hexdigest() != record["sha256"]:
                raise ValueError(f"checksum mismatch for {relative.name}")
            files[relative.name] = content
        notices = BUNDLED_NOTICES[package_id]
        selected = {**required, **notices}
        contents = {destination: files[name] for name, destination in selected.items()}
        upstream = {
            "package": package_id, "version": version, "url": package["source"],
            "distribution": "bundled",
            "files_sha256": {name: hashlib.sha256(content).hexdigest() for name, content in contents.items()},
        }
        return contents, upstream
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise SystemExit(f"Invalid bundled {package_id} template resources: {exc}. Restore or update the complete Prism repository. The initialization target was not changed.") from exc


def template_resources(
    template: str | None, variant: str | None = None, language: str | None = None,
) -> tuple[str, ...]:
    """Project-local upstream resources required by an initialized template."""
    sources = {
        "nature": NATURE_MEMBERS, "oup-numeric": BIB_MEMBERS,
        "oup-authoryear": BIOINFORMATICS_MEMBERS, "science": SCIENCE_MEMBERS,
    }
    source = template_profile(template, variant)["source"] if template else None
    resources = () if source == "nature" and variant != "sn-jnl" else (
        tuple(sources[source].values()) if source else ()
    )
    if template and language == "bilingual":
        resources += ("prism-cjk.sty",)
    if template:
        resources += template_profile(template, variant).get("resources", ())
    return resources


def _enable_bilingual(stage: Path, template: str) -> None:
    """Add CJK support to generated Prism-owned files, never upstream classes."""
    style = ASSET_DIR / "prism-cjk.sty"
    if not style.is_file():
        raise SystemExit("Bilingual template assets are missing: prism-cjk.sty")
    shutil.copy2(style, stage / "prism-cjk.sty")
    documents = ("examples.tex",) if template == "prism" else (
        "main.tex", "supplementary.tex", "examples.tex", "graphical_abstract.tex",
    )
    for name in documents:
        path = stage / name
        if not path.exists():
            continue  # Science Advances combines the supplement in main.tex.
        text = path.read_text(encoding="utf-8")
        text, count = re.subn(
            r"(?m)^(\\documentclass(?:\[[^\]\n]*\])?\{[^{}\n]+\}[^\S\n]*(?:%[^\n]*)?)(\r?\n|$)",
            lambda match: match.group(1) + match.group(2) + "\\usepackage{prism-cjk}\n",
            text, count=1,
        )
        if count != 1:
            raise SystemExit(f"Bilingual template is missing a supported document class: {name}")
        if name == "examples.tex":
            marker = r"\section{Bibliography mechanics}"
            if text.count(marker) != 1:
                raise SystemExit("Bilingual typesetting examples are missing their insertion point.")
            example = (
                "\\section{中英混排示例 / Bilingual example}\n"
                "这是合成的排版示例：English text、数字 123 和公式 $E=mc^2$。\n\n"
            )
            text = text.replace(marker, example + marker, 1)
        path.write_text(text, encoding="utf-8")


def _snapshot(target: Path) -> tuple | None:
    """Inventory existing content without following links before replacement."""
    if target.is_symlink():
        raise SystemExit(f"Initialization target must not be a symbolic link: {target}")
    if not target.exists():
        return None
    if not target.is_dir():
        raise SystemExit(f"Initialization target is not a directory: {target}")
    rows = []
    for directory, dirnames, filenames in os.walk(target, followlinks=False):
        for name in sorted((*dirnames, *filenames)):
            path = Path(directory) / name
            info = path.lstat()
            if path.is_symlink():
                content = os.readlink(path)
            elif path.is_file():
                content = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                content = None
            rows.append((str(path.relative_to(target)), info.st_mode, info.st_size, info.st_mtime_ns, content))
    info = target.stat()
    return (info.st_dev, info.st_ino, tuple(sorted(rows)))


def initialize(
    target: Path, force: bool, template: str = "prism", source: Path | None = None,
    language: str = "bilingual",
    article_type: str | None = None,
) -> int:
    try:
        template = resolve_template(template)
        selected_article = template_article_type(template, article_type)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if language not in ("bilingual", "english"):
        raise SystemExit("Invalid template language; use bilingual or english.")
    variant = ("sn-jnl" if source is not None else "prism-article") if template == "nature" else None
    profile = template_profile(template, variant)
    upstream_type = profile["source"]
    if source is not None and profile.get("bundled"):
        raise SystemExit("This maintained template does not accept --template-source; its reviewed resources are bundled.")
    # Do not resolve the final component: doing so would follow a target symlink.
    requested = Path(os.path.abspath(target.expanduser()))
    destination = requested.parent.resolve() / requested.name
    before = _snapshot(destination)
    if before is not None and before[2] and not force:
        raise SystemExit(f"Initialization target is not empty: {destination}")
    directory = "nature-official-template" if variant == "sn-jnl" else TEMPLATES[template]["directory"]
    asset = ASSET_DIR / directory
    multi_type = bool(TEMPLATES[template].get("article_types"))
    main_asset = asset / selected_article / "main.tex" if multi_type else asset / "main.tex"
    if not main_asset.is_file():
        raise SystemExit(f"Template assets are missing: {asset}")
    if multi_type:
        for name in profile.get("required_common", ()):
            if not (asset / "common" / name).is_file():
                raise SystemExit(f"Template assets are missing: {asset / 'common' / name}")
    for name in profile.get("shared_assets", ()):
        if not (ASSET_DIR / name).is_file():
            raise SystemExit(f"Shared template assets are missing: {ASSET_DIR / name}")
    examples = ASSET_DIR / "paper-template" / "examples.tex"
    if profile["examples"] and not examples.is_file():
        raise SystemExit(f"Shared typesetting examples are missing: {examples}")
    archive, members, bundled_upstream = (None, {}, None)
    if source is not None:
        source_path = source.expanduser().resolve()
        # Replacing a target must not retire or overwrite the supplied source.
        if (source_path == destination or destination in source_path.parents
                or (source_path.is_dir() and source_path in destination.parents)):
            raise SystemExit("Template source and initialization target must not overlap. The initialization target was not changed.")
    if upstream_type == "nature" and variant == "sn-jnl":
        archive, members = nature_package(source)
    elif upstream_type == "oup-numeric":
        if source is not None:
            archive, members = bib_package(source)
        else:
            members, bundled_upstream = _bundled_package("oup", {Path(name).name: dest for name, dest in BIB_MEMBERS.items()})
    elif upstream_type == "oup-authoryear":
        if source is not None:
            archive, members = bioinformatics_package(source)
        else:
            members, bundled_upstream = _bundled_package("oup", {Path(name).name: dest for name, dest in BIOINFORMATICS_MEMBERS.items()})
    elif upstream_type == "science":
        if source is not None:
            members = science_package(source)
        else:
            members, bundled_upstream = _bundled_package("science", SCIENCE_MEMBERS)
    if profile.get("bundled"):
        package_id, required = profile["bundled"]
        members, bundled_upstream = _bundled_package(package_id, required)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.prism-init-", dir=destination.parent))
    backup = None
    try:
        if multi_type:
            shutil.copytree(asset / "common", stage, dirs_exist_ok=True)
            shutil.copytree(asset / selected_article, stage, dirs_exist_ok=True)
        else:
            shutil.copytree(asset, stage, dirs_exist_ok=True)
        for name in profile.get("shared_assets", ()):
            shutil.copy2(ASSET_DIR / name, stage / name)
        if profile["examples"]:
            shutil.copy2(examples, stage / "examples.tex")
        if language == "bilingual":
            _enable_bilingual(stage, template)
        for name, content in members.items():
            (stage / name).write_bytes(content)
        metadata = {
            "schema_version": 1,
            "template": template,
            "template_id": TEMPLATES[template]["id"],
            "prism_version": project_version(),
            "engine": template_engine(template, "auto", language),
            "language": language,
        }
        if variant is not None:
            metadata["variant"] = variant
        if TEMPLATES[template].get("article_types"):
            metadata["article_type"] = selected_article
        if archive is not None:
            if upstream_type == "nature":
                upstream = {"url": NATURE_URL, "sha256": NATURE_SHA256, "archive": NATURE_ARCHIVE}
            else:
                upstream = {"url": BIB_URL, "sha256": BIB_SHA256, "archive": BIB_ARCHIVE}
            (stage / upstream["archive"]).write_bytes(archive)
            metadata["upstream"] = upstream
        elif bundled_upstream is not None:
            metadata["upstream"] = bundled_upstream
        elif upstream_type == "science":
            metadata["upstream"] = {
                "template": "Science-family v1.0 (July 2024)",
                "files_sha256": dict(SCIENCE_SHA256),
            }
        (stage / METADATA_NAME).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        if _snapshot(destination) != before:
            raise SystemExit("Initialization target changed during preparation; no existing files were moved.")
        if before is not None and before[2]:
            backup = destination.with_name(f"{destination.name}.backup")
            counter = 1
            while os.path.lexists(backup):
                backup = destination.with_name(f"{destination.name}.backup-{counter}")
                counter += 1
            destination.rename(backup)
        try:
            os.replace(stage, destination)
        except OSError:
            if backup is not None and not destination.exists():
                backup.rename(destination)
                backup = None
            raise
    except OSError as exc:
        raise SystemExit(f"Could not initialize manuscript: {exc}") from exc
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    if backup is not None:
        print(f"Backed up existing target: {backup}")
    print(f"Initialized paper ({template}): {destination}")
    return 0
