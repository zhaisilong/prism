"""Offline checks of declared recipes, local documentation and licensed assets."""
from __future__ import annotations

import re
from pathlib import Path
from .catalog import TemplateCatalog, relative_path
from . import template_assets
from .template_assets import AssetContext


def _checked_path(root: Path, relative: str, *, directory: bool = False) -> Path:
    relative_path(relative)
    path = root / relative
    for item in (root, *[root.joinpath(*Path(relative).parts[:i]) for i in range(1, len(Path(relative).parts) + 1)]):
        if item.is_symlink():
            raise ValueError("symbolic links are not allowed")
    if root.resolve() not in path.resolve().parents:
        raise ValueError("path escapes its declared root")
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError("missing directory" if directory else "missing file")
    return path


def validate_catalog(catalog: TemplateCatalog, repo_dir: Path, asset_dir: Path) -> tuple[str, ...]:
    """Return safe relative diagnostics; never invoke TeX, the network or writes."""
    issues = []
    try:
        catalog.choices()
    except ValueError as exc:
        return (str(exc),)
    for alias, record in catalog.templates.items():
        profile = catalog.profile(alias)
        required = ["prism-cjk.sty", *profile.shared_assets,
                    *(f"{record.directory}/{name}" for name in record.required_assets)]
        if profile.examples:
            required.append("paper-template/examples.tex")
        for article in record.article_types or (record.article_type,):
            prefix = record.directory
            if record.supports_article_type:
                required.extend(f"{prefix}/common/{name}" for name in profile.required_common)
                required.append(f"{prefix}/{article}/main.tex")
                for role in record.documents:
                    if role.path in ("main.tex", "examples.tex"):
                        continue
                    # Selected content may override common files (e.g. review SI).
                    selected = asset_dir / prefix / article / role.path
                    required.append(f"{prefix}/{article}/{role.path}" if selected.exists() else f"{prefix}/common/{role.path}")
                required.append(f"{prefix}/common/references.bib")
            else:
                required.extend(f"{prefix}/{role.path}" for role in record.documents if role.path != "examples.tex" or not profile.examples)
                required.append(f"{prefix}/references.bib")
        if alias == "nature":
            required.extend(f"nature-official-template/{name}" for name in ("main.tex", "supplementary.tex", "references.bib"))
        for relative in dict.fromkeys(required):
            try:
                _checked_path(asset_dir, relative)
            except ValueError as exc:
                issues.append(f"{alias}: {relative}: {exc}")
        # The whole copied tree is checked as well as the declared entrypoints.
        try:
            directory = _checked_path(asset_dir, record.directory, directory=True)
            for path in directory.rglob("*"):
                if path.is_symlink() or not (path.is_file() or path.is_dir()):
                    issues.append(f"{alias}: unsafe asset path in {record.directory}")
                    break
        except ValueError as exc:
            issues.append(f"{alias}: {record.directory}: {exc}")
        try:
            guide = _checked_path(repo_dir, record.guide_path)
            for destination in re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", guide.read_text(encoding="utf-8")):
                if destination.startswith(("https://", "http://", "mailto:", "#")):
                    continue
                link_path = destination.split("#", 1)[0]
                linked = guide.parent / link_path
                if linked.is_symlink() or repo_dir.resolve() not in linked.resolve().parents or not linked.is_file():
                    raise ValueError("broken or unsafe local guide link")
        except (OSError, ValueError) as exc:
            issues.append(f"{alias}: {record.guide_path}: {exc}")
    # Reading any selection verifies every manifest member, including LICENSE,
    # NOTICE and unselected shared styles, against size and SHA-256.
    context = AssetContext(asset_dir)
    packages = set()
    for record in catalog.templates.values():
        profile = catalog.profile(record.alias)
        if profile.source in ("oup-numeric", "oup-authoryear"):
            packages.add("oup")
        elif profile.source == "science":
            packages.add("science")
        if profile.bundled:
            packages.add(profile.bundled[0])
    for package in sorted(packages):
        try:
            template_assets._bundled_package(package, {}, context=context)
        except SystemExit:
            issues.append(f"upstream/{package}: invalid manifest, licensed files or checksum")
    return tuple(dict.fromkeys(issues))
