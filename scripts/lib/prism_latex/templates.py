"""Small, pinned template catalog and safe manuscript initialization."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import TypedDict

from .build_support import project_version


PROJECT_DIR = Path(__file__).resolve().parents[3]
ASSET_DIR = PROJECT_DIR / "skills" / "paper-latex" / "assets"
METADATA_NAME = "prism-template.json"
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
        "description": "Nature / NMI manuscript and supplementary information; English; pdfLaTeX",
    },
    "nature-communications": {
        "id": "journal/nature-communications", "kind": "journal", "venue": "Nature Communications",
        "publisher": "Springer Nature", "article_type": "research", "backend": "nature-communications",
        "directory": "nature-communications-template",
        "engine": "pdflatex",
        "description": "Nature Communications research article and supplementary information; English; pdfLaTeX",
    },
    "science-advances": {
        "id": "journal/science-advances", "kind": "journal", "venue": "Science Advances",
        "publisher": "AAAS", "article_type": "research", "backend": "science",
        "directory": "science-advances-template",
        "engine": "pdflatex",
        "description": "Science Advances research article and combined supplementary material; English; pdfLaTeX",
    },
    "bib": {
        "id": "journal/briefings-in-bioinformatics", "kind": "journal", "venue": "Briefings in Bioinformatics",
        "publisher": "Oxford University Press", "article_type": "manuscript", "backend": "oup-numeric",
        "directory": "bib-template",
        "engine": "pdflatex",
        "description": "Briefings in Bioinformatics (OUP); English; pdfLaTeX",
    },
    "ddt": {
        "id": "journal/drug-discovery-today", "kind": "journal", "venue": "Drug Discovery Today",
        "publisher": "Elsevier", "article_type": "review", "backend": "ddt",
        "directory": "ddt-template",
        "engine": "pdflatex",
        "description": "Drug Discovery Today narrative review (Elsevier); English; pdfLaTeX",
    },
    "jcim": {
        "id": "journal/jcim", "kind": "journal", "venue": "Journal of Chemical Information and Modeling",
        "publisher": "ACS", "article_type": "research", "backend": "acs",
        "directory": "jcim-template",
        "engine": "pdflatex",
        "description": "Journal of Chemical Information and Modeling research article (ACS); English; pdfLaTeX",
    },
    "jacs": {
        "id": "journal/jacs", "kind": "journal", "venue": "Journal of the American Chemical Society",
        "publisher": "ACS", "article_type": "research", "backend": "acs",
        "directory": "jacs-template", "engine": "pdflatex",
        "description": "Journal of the American Chemical Society research article (ACS); English; pdfLaTeX",
    },
    "bioinformatics": {
        "id": "journal/bioinformatics", "kind": "journal", "venue": "Bioinformatics",
        "publisher": "Oxford University Press", "article_type": "original", "backend": "oup-authoryear",
        "directory": "bioinformatics-template", "engine": "pdflatex",
        "description": "Bioinformatics original paper (OUP); English; pdfLaTeX",
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
    "article.cls", "graphicx.sty", "amsmath.sty", "amssymb.sty",
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


BUILD_PROFILES = {
    "prism": {"packages": PRISM_PACKAGES, "source": None, "examples": False},
    "nature": {"packages": NATURE_PACKAGES, "source": "nature", "examples": True},
    "nature-communications": {"packages": NATURE_COMMUNICATIONS_PACKAGES, "source": None, "examples": True},
    "science": {"packages": SCIENCE_PACKAGES, "source": "science", "examples": True},
    "oup-numeric": {"packages": BIB_PACKAGES, "source": "oup-numeric", "examples": True},
    "oup-authoryear": {"packages": BIB_PACKAGES + ("unsrtnat.bst",), "source": "oup-authoryear", "examples": True},
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
        names.extend((alias, canonical))
    return tuple(names)


def resolve_template(name: str) -> str:
    """Resolve a stable ID or legacy alias to its compatibility alias."""
    template_choices()
    for alias, details in TEMPLATES.items():
        if name == alias or name == details["id"]:
            return alias
    raise ValueError(f"unknown template: {name}")


def template_profile(template: str) -> dict:
    alias = resolve_template(template)
    return BUILD_PROFILES[TEMPLATES[alias]["backend"]]


def template_isolated_build(template: str | None) -> bool:
    return bool(template and template_profile(template).get("isolate_cwd", False))


def template_for_project(project: Path) -> str | None:
    path = project / METADATA_NAME
    if not path.exists():
        return None
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        template = resolve_template(metadata["template"])
        if "schema_version" in metadata or "template_id" in metadata:
            if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1:
                raise ValueError("unsupported template metadata schema version")
            if metadata.get("template_id") != TEMPLATES[template]["id"]:
                raise ValueError("template and template_id do not match")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(f"Invalid Prism template metadata: {path}: {exc}") from exc
    return template


def template_engine(template: str | None, requested: str) -> str:
    alias = resolve_template(template) if template else None
    if alias and TEMPLATES[alias]["backend"] == "prism" and requested == "pdflatex":
        raise SystemExit("The prism template requires XeLaTeX or LuaLaTeX; use --engine auto, xelatex, or lualatex.")
    if alias and TEMPLATES[alias]["engine"] == "pdflatex":
        if requested not in ("auto", "pdflatex"):
            raise SystemExit(f"The {alias} template requires pdfLaTeX; use --engine auto or pdflatex.")
        return "pdflatex"
    return requested


def template_packages(template: str | None, engine: str) -> tuple[str, ...]:
    engine = template_engine(template, engine)
    if template:
        return template_profile(template)["packages"]
    # Existing, unmarked projects can explicitly request pdfLaTeX too.
    if engine == "pdflatex":
        return ("graphicx.sty", "amsmath.sty", "amssymb.sty", "natbib.sty")
    return PRISM_PACKAGES


def _pinned_package(
    source: Path | None, *, label: str, url: str, size: int,
    sha256: str, required: dict[str, str],
) -> tuple[bytes, dict[str, bytes]]:
    """Validate one original archive in memory and read only named resources."""
    try:
        if source is not None:
            with source.expanduser().open("rb") as handle:
                archive = handle.read(size + 1)
        else:
            request = urllib.request.Request(url, headers={"User-Agent": "Prism-LaTeX"})
            with urllib.request.urlopen(request, timeout=30) as response:
                archive = response.read(size + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise SystemExit(f"Cannot read the pinned {label} template package: {exc}. Use --template-source PACKAGE.zip for offline initialization.") from exc
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
        source, label="Nature", url=NATURE_URL, size=NATURE_SIZE,
        sha256=NATURE_SHA256, required=NATURE_MEMBERS,
    )


def bib_package(source: Path | None) -> tuple[bytes, dict[str, bytes]]:
    return _pinned_package(
        source, label="BIB", url=BIB_URL, size=BIB_SIZE,
        sha256=BIB_SHA256, required=BIB_MEMBERS,
    )


def bioinformatics_package(source: Path | None) -> tuple[bytes, dict[str, bytes]]:
    return _pinned_package(
        source, label="Bioinformatics", url=BIB_URL, size=BIB_SIZE,
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


def template_resources(template: str | None) -> tuple[str, ...]:
    """Project-local upstream resources required by an initialized template."""
    sources = {
        "nature": NATURE_MEMBERS, "oup-numeric": BIB_MEMBERS,
        "oup-authoryear": BIOINFORMATICS_MEMBERS, "science": SCIENCE_MEMBERS,
    }
    source = template_profile(template)["source"] if template else None
    return tuple(sources[source].values()) if source else ()


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


def initialize(target: Path, force: bool, template: str = "prism", source: Path | None = None) -> int:
    try:
        template = resolve_template(template)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    profile = template_profile(template)
    upstream_type = profile["source"]
    # Do not resolve the final component: doing so would follow a target symlink.
    requested = Path(os.path.abspath(target.expanduser()))
    destination = requested.parent.resolve() / requested.name
    before = _snapshot(destination)
    if before is not None and before[2] and not force:
        raise SystemExit(f"Initialization target is not empty: {destination}")
    asset = ASSET_DIR / TEMPLATES[template]["directory"]
    if not (asset / "main.tex").is_file():
        raise SystemExit(f"Template assets are missing: {asset}")
    examples = ASSET_DIR / "paper-template" / "examples.tex"
    if profile["examples"] and not examples.is_file():
        raise SystemExit(f"Shared typesetting examples are missing: {examples}")
    archive, members = (None, {})
    if upstream_type == "nature":
        archive, members = nature_package(source)
    elif upstream_type == "oup-numeric":
        archive, members = bib_package(source)
    elif upstream_type == "oup-authoryear":
        archive, members = bioinformatics_package(source)
    elif upstream_type == "science":
        if source is not None:
            source_path = source.expanduser().resolve()
            # Do not move the source when replacing a target, or write the
            # generated project into the user's supplied template directory.
            if (source_path == destination or destination in source_path.parents
                    or (source_path.is_dir() and source_path in destination.parents)):
                raise SystemExit("Science template source and initialization target must not overlap. The initialization target was not changed.")
        members = science_package(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.prism-init-", dir=destination.parent))
    backup = None
    try:
        shutil.copytree(asset, stage, dirs_exist_ok=True)
        if profile["examples"]:
            shutil.copy2(examples, stage / "examples.tex")
        for name, content in members.items():
            (stage / name).write_bytes(content)
        metadata = {
            "schema_version": 1,
            "template": template,
            "template_id": TEMPLATES[template]["id"],
            "prism_version": project_version(),
            "engine": TEMPLATES[template]["engine"],
        }
        if archive is not None:
            if upstream_type == "nature":
                upstream = {"url": NATURE_URL, "sha256": NATURE_SHA256, "archive": NATURE_ARCHIVE}
            else:
                upstream = {"url": BIB_URL, "sha256": BIB_SHA256, "archive": BIB_ARCHIVE}
            (stage / upstream["archive"]).write_bytes(archive)
            metadata["upstream"] = upstream
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
