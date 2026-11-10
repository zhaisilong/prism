"""Bounded local source readers and pinned upstream resource verification."""
from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from .paths import ASSET_DIR

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


@dataclass(frozen=True)
class AssetContext:
    root: Path = ASSET_DIR
    nature_size: int = NATURE_SIZE
    nature_sha256: str = NATURE_SHA256
    bib_size: int = BIB_SIZE
    bib_sha256: str = BIB_SHA256
    science_sha256: Mapping[str, str] = field(default_factory=lambda: MappingProxyType(dict(SCIENCE_SHA256)))

    def __post_init__(self):
        object.__setattr__(self, "root", Path(self.root))
        object.__setattr__(self, "science_sha256", MappingProxyType(dict(self.science_sha256)))

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

def nature_package(source: Path | None, *, context: AssetContext | None = None) -> tuple[bytes, dict[str, bytes]]:
    context = context or AssetContext()
    return _pinned_package(
        source, label="Nature", size=context.nature_size,
        sha256=context.nature_sha256, required=NATURE_MEMBERS,
    )

def bib_package(source: Path | None, *, context: AssetContext | None = None) -> tuple[bytes, dict[str, bytes]]:
    context = context or AssetContext()
    return _pinned_package(
        source, label="BIB", size=context.bib_size,
        sha256=context.bib_sha256, required=BIB_MEMBERS,
    )

def bioinformatics_package(source: Path | None, *, context: AssetContext | None = None) -> tuple[bytes, dict[str, bytes]]:
    context = context or AssetContext()
    return _pinned_package(
        source, label="Bioinformatics", size=context.bib_size,
        sha256=context.bib_sha256, required=BIOINFORMATICS_MEMBERS,
    )

def _read_science_file(path: Path, limit: int, *, inventory: list | None = None) -> bytes:
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
        if inventory is not None:
            inventory.append((path, after.st_size, after.st_mtime_ns, hashlib.sha256(content).hexdigest()))
        return content

def science_package(source: Path | None, *, context: AssetContext | None = None) -> dict[str, bytes]:
    """Read the pinned Science v1.0 files from a user-supplied folder or ZIP.

    Hashes establish reproducibility against this recorded version; they do not
    independently authenticate a user-supplied package's provenance.
    """
    context = context or AssetContext()
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
            if hashlib.sha256(content).hexdigest() != context.science_sha256[name]:
                raise ValueError(f"checksum mismatch for {name}; expected Science-family v1.0")
        return {SCIENCE_MEMBERS[name]: content for name, content in contents.items()}
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise SystemExit(f"Invalid Science-family template source: {exc}. The initialization target was not changed.") from exc

def _bundled_package(package_id: str, required: dict[str, str], *, context: AssetContext | None = None, inventory: list | None = None) -> tuple[dict[str, bytes], dict]:
    """Verify the maintained source selection before touching a target."""
    context = context or AssetContext()
    root = context.root / "upstream"
    if context.root.is_symlink() or root.is_symlink():
        raise SystemExit("Invalid bundled template resources: symbolic links are not allowed.")
    version, directory = BUNDLED_PACKAGES[package_id]
    try:
        manifest = json.loads(_read_science_file(root / "manifest.json", 100_000, inventory=inventory).decode("utf-8"))
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
            if any((root / parent).is_symlink() for parent in (*relative.parents, relative)):
                raise ValueError("bundled path contains a symbolic link")
            content = _read_science_file(root / relative, size, inventory=inventory)
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
