"""Plan project files before staging and safely replace the requested directory."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
from .build_support import project_version
from .catalog import CATALOG, BuildProfile, TemplateCatalog, relative_path, template_engine
from .paths import METADATA_NAME
from . import template_assets as sources
from .template_assets import AssetContext


@dataclass(frozen=True)
class GeneratedFile:
    path: str
    content: bytes
    mode: int = 0o644

    def __post_init__(self):
        relative_path(self.path)
        if not isinstance(self.content, bytes) or type(self.mode) is not int:
            raise ValueError("Invalid generated file")


@dataclass(frozen=True)
class InitializationPlan:
    template: str
    article_type: str
    language: str
    variant: str | None
    destination: Path
    before: tuple | None
    files: tuple[GeneratedFile, ...]
    source_inventory: tuple[tuple[Path, int, int, str], ...]


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


def _collect_assets(directory: Path, files: dict[str, GeneratedFile], inventory: list) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise SystemExit(f"Template assets are missing or unsafe: {directory}")
    for root, directories, names in os.walk(directory, followlinks=False):
        for name in directories:
            if (Path(root) / name).is_symlink():
                raise SystemExit("Template assets must not contain symbolic links.")
        for name in sorted(names):
            path = Path(root) / name
            content = sources._read_science_file(path, 2_000_000)
            info = path.stat()
            relative = path.relative_to(directory).as_posix()
            files[relative] = GeneratedFile(relative, content, stat.S_IMODE(info.st_mode))
            inventory.append((path, info.st_size, info.st_mtime_ns, hashlib.sha256(content).hexdigest()))


def _add_asset(path: Path, destination: str, files: dict, inventory: list) -> None:
    if path.is_symlink():
        raise SystemExit("Template assets must not contain symbolic links.")
    content = sources._read_science_file(path, 2_000_000)
    info = path.stat()
    files[destination] = GeneratedFile(destination, content, stat.S_IMODE(info.st_mode))
    inventory.append((path, info.st_size, info.st_mtime_ns, hashlib.sha256(content).hexdigest()))


def _enable_bilingual(files: dict[str, GeneratedFile], template: str, context: AssetContext, inventory: list) -> None:
    style = context.root / "prism-cjk.sty"
    if not style.is_file():
        raise SystemExit("Bilingual template assets are missing: prism-cjk.sty")
    _add_asset(style, "prism-cjk.sty", files, inventory)
    documents = ("examples.tex",) if template == "prism" else (
        "main.tex", "supplementary.tex", "examples.tex", "graphical_abstract.tex",
    )
    for name in documents:
        if name not in files:
            continue  # Science Advances combines the supplement in main.tex.
        original = files[name]
        text = original.content.decode("utf-8")
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
        files[name] = GeneratedFile(name, text.encode("utf-8"), original.mode)


def plan_initialization(
    target: Path, force: bool, template: str = "prism", source: Path | None = None,
    language: str = "bilingual", article_type: str | None = None, *,
    catalog: TemplateCatalog = CATALOG, context: AssetContext | None = None,
    source_readers: Mapping[str, Callable] | None = None,
) -> InitializationPlan:
    context = context or AssetContext()
    readers = source_readers or {
        "nature": lambda source: sources.nature_package(source, context=context),
        "oup-numeric": lambda source: sources.bib_package(source, context=context),
        "oup-authoryear": lambda source: sources.bioinformatics_package(source, context=context),
        "science": lambda source: sources.science_package(source, context=context),
    }
    try:
        template = catalog.resolve(template)
        selected_article = catalog.article_type(template, article_type)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if language not in ("bilingual", "english"):
        raise SystemExit("Invalid template language; use bilingual or english.")
    variant = ("sn-jnl" if source is not None else "prism-article") if template == "nature" else None
    record = catalog.templates[template]
    profile = catalog.profile(template, variant)
    upstream_type = profile.source
    if source is not None and profile.bundled:
        raise SystemExit("This maintained template does not accept --template-source; its reviewed resources are bundled.")
    requested = Path(os.path.abspath(target.expanduser()))
    destination = requested.parent.resolve() / requested.name
    before = _snapshot(destination)
    if before is not None and before[2] and not force:
        raise SystemExit(f"Initialization target is not empty: {destination}")
    directory = "nature-official-template" if variant == "sn-jnl" else record.directory
    asset = context.root / directory
    if context.root.is_symlink() or asset.is_symlink():
        raise SystemExit("Template assets must not contain symbolic links.")
    multi_type = record.supports_article_type
    main_asset = asset / selected_article / "main.tex" if multi_type else asset / "main.tex"
    if not main_asset.is_file():
        raise SystemExit(f"Template assets are missing: {asset}")
    if multi_type:
        for name in profile.required_common:
            if not (asset / "common" / name).is_file():
                raise SystemExit(f"Template assets are missing: {asset / 'common' / name}")
    for name in profile.shared_assets:
        if not (context.root / name).is_file():
            raise SystemExit(f"Shared template assets are missing: {context.root / name}")
    for name in record.required_assets:
        if not (asset / name).is_file():
            raise SystemExit(f"Template assets are missing: {asset / name}")
    examples = context.root / "paper-template" / "examples.tex"
    if profile.examples and not examples.is_file():
        raise SystemExit(f"Shared typesetting examples are missing: {examples}")
    archive, members, bundled_upstream = None, {}, None
    inventory = []
    if source is not None:
        source_path = source.expanduser().resolve()
        if (source_path == destination or destination in source_path.parents
                or (source_path.is_dir() and source_path in destination.parents)):
            raise SystemExit("Template source and initialization target must not overlap. The initialization target was not changed.")
    if upstream_type == "nature" and variant == "sn-jnl":
        archive, members = readers[upstream_type](source)
    elif upstream_type in ("oup-numeric", "oup-authoryear"):
        if source is not None:
            archive, members = readers[upstream_type](source)
        else:
            required = sources.BIB_MEMBERS if upstream_type == "oup-numeric" else sources.BIOINFORMATICS_MEMBERS
            members, bundled_upstream = sources._bundled_package("oup", {Path(name).name: dest for name, dest in required.items()}, context=context, inventory=inventory)
    elif upstream_type == "science":
        if source is not None:
            members = readers[upstream_type](source)
        else:
            members, bundled_upstream = sources._bundled_package("science", sources.SCIENCE_MEMBERS, context=context, inventory=inventory)
    if profile.bundled:
        package_id, required = profile.bundled
        members, bundled_upstream = sources._bundled_package(package_id, required, context=context, inventory=inventory)
    files: dict[str, GeneratedFile] = {}
    try:
        if multi_type:
            _collect_assets(asset / "common", files, inventory)
            _collect_assets(asset / selected_article, files, inventory)
        else:
            _collect_assets(asset, files, inventory)
        for name in profile.shared_assets:
            _add_asset(context.root / name, name, files, inventory)
        if profile.examples:
            _add_asset(examples, "examples.tex", files, inventory)
        if language == "bilingual":
            _enable_bilingual(files, template, context, inventory)
        for name, content in members.items():
            files[name] = GeneratedFile(name, content)
        # Engine selection keeps the catalog's policy; custom catalogs are
        # intentionally small test fixtures with one of these two policies.
        engine = "xelatex" if language == "bilingual" and record.engine == "pdflatex" else record.engine
        metadata = {"schema_version": 1, "template": template, "template_id": record.id,
                    "prism_version": project_version(), "engine": engine, "language": language}
        if variant is not None:
            metadata["variant"] = variant
        if multi_type:
            metadata["article_type"] = selected_article
        if archive is not None:
            if upstream_type == "nature":
                upstream = {"url": sources.NATURE_URL, "sha256": context.nature_sha256, "archive": sources.NATURE_ARCHIVE}
            else:
                upstream = {"url": sources.BIB_URL, "sha256": context.bib_sha256, "archive": sources.BIB_ARCHIVE}
            files[upstream["archive"]] = GeneratedFile(upstream["archive"], archive)
            metadata["upstream"] = upstream
        elif bundled_upstream is not None:
            metadata["upstream"] = bundled_upstream
        elif upstream_type == "science":
            metadata["upstream"] = {"template": "Science-family v1.0 (July 2024)", "files_sha256": dict(context.science_sha256)}
        files[METADATA_NAME] = GeneratedFile(METADATA_NAME, (json.dumps(metadata, indent=2) + "\n").encode("utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Could not initialize manuscript: {exc}") from exc
    return InitializationPlan(template, selected_article, language, variant, destination, before, tuple(files.values()), tuple(inventory))


def _verify_plan(plan: InitializationPlan):
    if _snapshot(plan.destination) != plan.before:
        raise SystemExit("Initialization target changed during preparation; no existing files were moved.")
    for path, size, modified, digest in plan.source_inventory:
        try:
            content = sources._read_science_file(path, size)
            info = path.stat()
            unchanged = (info.st_size, info.st_mtime_ns, hashlib.sha256(content).hexdigest()) == (size, modified, digest)
        except (OSError, ValueError):
            unchanged = False
        if not unchanged:
            raise SystemExit("Template assets changed during preparation; no existing files were moved.")


def apply_initialization(plan: InitializationPlan) -> int:
    destination = plan.destination
    _verify_plan(plan)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.prism-init-", dir=destination.parent))
    backup = None
    try:
        for file in plan.files:
            target = stage / file.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(file.content)
            target.chmod(file.mode)
        _verify_plan(plan)
        if plan.before is not None and plan.before[2]:
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
    print(f"Initialized paper ({plan.template}): {destination}")
    return 0


def initialize(target: Path, force: bool, template: str = "prism", source: Path | None = None,
               language: str = "bilingual", article_type: str | None = None, **kwargs) -> int:
    return apply_initialization(plan_initialization(target, force, template, source, language, article_type, **kwargs))
