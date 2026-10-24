#!/usr/bin/env python3
"""Audit and export a fresh, text-only Prism code snapshot without Git history."""

from __future__ import annotations

import argparse
import collections
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from dataclasses import dataclass


ROOT_FILES = frozenset({".gitignore", "AGENTS.md", "CHANGELOG.md", "LICENSE", "README.md", "VERSION"})
SOURCE_DIRS = frozenset({"scripts", "skills", "tests", "docs"})
TEXT_SUFFIXES = frozenset({
    ".md", ".rst", ".txt", ".py", ".sh", ".tex", ".sty", ".bib", ".cls", ".bst",
    ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".csl", ".dtx", ".ins",
})
TEXT_NAMES = frozenset({"LICENSE", "NOTICE", "COPYING", "Makefile", "VERSION", ".gitignore", ".gitkeep", ".latexmkrc"})
CACHE_DIRS = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache", ".tox",
    ".venv", "node_modules", "build", "dist", "out", "tmp", "temp",
})
GENERATED_SUFFIXES = frozenset({
    ".pyc", ".pyo", ".aux", ".bbl", ".bcf", ".blg", ".fdb_latexmk", ".fls",
    ".idx", ".ilg", ".ind", ".lof", ".log", ".lot", ".out", ".toc",
})
METADATA_NAMES = frozenset({".git", ".hg", ".svn"})
MAX_TEXT_BYTES = 5 * 1024 * 1024

# Match concrete paths and credentials, not their regex definitions in this file.
PRIVATE_PATTERNS = (
    ("absolute-home-path", re.compile("/" + "(?:Users|home)" + "/" + r"[^/\s]+(?:/|\b)")),
    ("absolute-windows-home-path", re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.I)),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b")),
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----")),
)
EMAIL = re.compile(r"[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})", re.I)
EXAMPLE_DOMAINS = frozenset({"example.com", "example.net", "example.org"})


class ExportError(Exception):
    """An audit or publication error safe to show without matched values."""


@dataclass(frozen=True)
class Entry:
    path: str
    size: int
    sha256: str
    mode: int
    signature: tuple[int, ...]

    def public_record(self):
        return {"path": self.path, "size": self.size, "sha256": self.sha256, "mode": oct(self.mode)}


@dataclass
class Inventory:
    entries: list[Entry]
    exclusions: collections.Counter


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, stat.S_IMODE(info.st_mode))


def _read_regular(source: Path, relative: str):
    """Open every component without following links, including during races."""
    parts = Path(relative).parts
    descriptors = []
    try:
        current = os.open(source, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=current)
            descriptors.append(current)
        handle = os.open(parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), dir_fd=current)
        descriptors.append(handle)
        before = os.fstat(handle)
        if not stat.S_ISREG(before.st_mode):
            raise ExportError(f"{relative}: non-regular-file")
        if before.st_size > MAX_TEXT_BYTES:
            raise ExportError(f"{relative}: text-file-too-large")
        with os.fdopen(os.dup(handle), "rb") as stream:
            data = stream.read(MAX_TEXT_BYTES + 1)
        after = os.fstat(handle)
        if _signature(before) != _signature(after) or len(data) != before.st_size:
            raise ExportError(f"{relative}: source-changed")
        return data, before
    except OSError as exc:
        raise ExportError(f"{relative}: unsafe-or-unreadable-source ({exc.errno})") from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _privacy_rules(text: str):
    rules = {name for name, pattern in PRIVATE_PATTERNS if pattern.search(text)}
    for match in EMAIL.finditer(text):
        domain = match.group(1).lower()
        if not any(domain == allowed or domain.endswith("." + allowed) for allowed in EXAMPLE_DOMAINS):
            rules.add("non-example-email")
    return sorted(rules)


def inventory(source: Path) -> Inventory:
    entries = []
    exclusions = collections.Counter()
    findings = []

    def inspect(path: Path):
        relative = path.relative_to(source).as_posix()
        try:
            info = path.lstat()
        except OSError as exc:
            raise ExportError(f"{relative}: unreadable-source ({exc.errno})") from None
        if stat.S_ISLNK(info.st_mode):
            findings.append(f"{relative}: symlink")
            return
        if path.name in METADATA_NAMES:
            findings.append(f"{relative}: nested-repository-metadata")
            return
        if stat.S_ISDIR(info.st_mode):
            if path.name in CACHE_DIRS:
                exclusions["generated-directories"] += 1
                return
            if path.name.startswith("."):
                findings.append(f"{relative}: unrecognized-hidden-directory")
                return
            try:
                children = sorted(path.iterdir(), key=lambda child: child.name)
            except OSError as exc:
                raise ExportError(f"{relative}: unreadable-directory ({exc.errno})") from None
            for child in children:
                inspect(child)
            return
        if not stat.S_ISREG(info.st_mode):
            findings.append(f"{relative}: non-regular-file")
            return
        if (path.name == ".DS_Store" or path.suffix.lower() in GENERATED_SUFFIXES
                or path.name.endswith((".run.xml", ".synctex.gz"))):
            exclusions["generated-files"] += 1
            return
        if path.name not in ROOT_FILES | TEXT_NAMES and path.suffix.lower() not in TEXT_SUFFIXES:
            findings.append(f"{relative}: unrecognized-file-type")
            return
        if path.name.startswith(".") and path.name not in TEXT_NAMES:
            findings.append(f"{relative}: unrecognized-hidden-file")
            return
        data, opened = _read_regular(source, relative)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(f"{relative}: binary-or-non-utf8-content")
            return
        if any(ord(char) < 32 and char not in "\t\r\n\f" for char in text):
            findings.append(f"{relative}: binary-control-characters")
            return
        for rule in _privacy_rules(text + "\n" + relative):
            findings.append(f"{relative}: {rule}")
        entries.append(Entry(relative, len(data), hashlib.sha256(data).hexdigest(),
                             0o755 if opened.st_mode & 0o111 else 0o644, _signature(opened)))

    if not source.is_dir():
        raise ExportError("Source must be an existing directory.")
    for path in sorted(source.iterdir(), key=lambda item: item.name):
        if path.name in ROOT_FILES or path.name in SOURCE_DIRS:
            if path.name in ROOT_FILES and path.is_dir() and not path.is_symlink():
                findings.append(f"{path.name}: expected-root-file")
            elif path.name in SOURCE_DIRS and not path.is_dir() and not path.is_symlink():
                findings.append(f"{path.name}: expected-source-directory")
            else:
                inspect(path)
        elif path.name == "projects":
            if path.is_symlink():
                findings.append("projects: symlink")
            elif path.is_dir():
                placeholder = path / ".gitkeep"
                if placeholder.exists() or placeholder.is_symlink():
                    if placeholder.is_dir():
                        findings.append("projects/.gitkeep: expected-placeholder-file")
                    else:
                        inspect(placeholder)
                exclusions["local-data-roots"] += 1
        else:
            # Deliberately do not traverse ignored or unrecognized root entries.
            exclusions["outside-allowlist-roots"] += 1
    if findings:
        raise ExportError("Audit failed:\n" + "\n".join(findings))
    if not entries:
        raise ExportError("No allowlisted source files found.")
    return Inventory(sorted(entries, key=lambda entry: entry.path), exclusions)


def _inside(path: Path, parent: Path):
    return path == parent or parent in path.parents


def _in_export_boundary(path: Path, source: Path):
    if not _inside(path, source):
        return False
    relative = path.relative_to(source)
    return (not relative.parts or relative.parts[0] in SOURCE_DIRS
            or relative.as_posix() in ROOT_FILES
            or relative.as_posix() == "projects/.gitkeep")


def _publish_directory(staged: Path, destination: Path):
    """Atomically rename without replacing even an empty competing directory."""
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename = library.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(os.fsencode(staged), os.fsencode(destination), 0x00000004)  # RENAME_EXCL
    elif sys.platform.startswith("linux") and hasattr(library, "renameat2"):
        rename = library.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(-100, os.fsencode(staged), -100, os.fsencode(destination), 1)  # RENAME_NOREPLACE
    else:
        raise ExportError("Atomic non-replacing directory export requires macOS or Linux with renameat2.")
    if result:
        code = ctypes.get_errno()
        if code in (errno.EEXIST, errno.ENOTEMPTY):
            raise ExportError("Output already exists; choose a new directory.")
        raise ExportError(f"Atomic publication failed ({code}).")


def export(source: Path, destination: Path, manifest: Path | None = None):
    source = source.resolve()
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise ExportError("Output already exists; choose a new directory.")
    destination = destination.parent.resolve() / destination.name
    if any(part.casefold() in METADATA_NAMES for part in destination.parts):
        raise ExportError("Output must be outside repository metadata directories.")
    if not destination.parent.is_dir():
        raise ExportError("Output parent must already exist.")
    if _in_export_boundary(destination, source):
        raise ExportError("Output must be outside the exported source boundaries.")
    if manifest is not None:
        manifest = manifest.absolute()
        if manifest.exists() or manifest.is_symlink():
            raise ExportError("Manifest already exists; choose a new file.")
        manifest = manifest.parent.resolve() / manifest.name
        if any(part.casefold() in METADATA_NAMES for part in manifest.parts):
            raise ExportError("Manifest must be outside repository metadata directories.")
        if not manifest.parent.is_dir():
            raise ExportError("Manifest parent must already exist.")
        if _inside(manifest, destination) or _in_export_boundary(manifest, source):
            raise ExportError("Manifest must be outside the snapshot and exported source boundaries.")
    initial = inventory(source)
    with tempfile.TemporaryDirectory(prefix=".prism-export-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "snapshot"
        staged.mkdir()
        for entry in initial.entries:
            data, info = _read_regular(source, entry.path)
            if (_signature(info) != entry.signature or hashlib.sha256(data).hexdigest() != entry.sha256):
                raise ExportError(f"{entry.path}: source-changed")
            target = staged / entry.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(entry.mode)
            if target.stat().st_size != entry.size or hashlib.sha256(target.read_bytes()).hexdigest() != entry.sha256:
                raise ExportError(f"{entry.path}: copy-verification-failed")
        final = inventory(source)
        if initial.entries != final.entries:
            raise ExportError("Source changed during export; no snapshot was published.")
        manifest_data = {
            "format": 1,
            "file_count": len(initial.entries),
            "total_bytes": sum(entry.size for entry in initial.entries),
            "exclusions": dict(initial.exclusions),
            "files": [entry.public_record() for entry in initial.entries],
        }
        manifest_identity = None
        if manifest is not None:
            # Stage beside the manifest so publication also works when its
            # filesystem differs from the snapshot's filesystem.
            with tempfile.TemporaryDirectory(prefix=".prism-manifest-", dir=manifest.parent) as manifest_temporary:
                manifest_stage = Path(manifest_temporary) / "manifest.json"
                manifest_stage.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                manifest_stage.chmod(0o600)
                try:
                    os.link(manifest_stage, manifest)
                    manifest_identity = manifest_stage.stat().st_ino
                except OSError as exc:
                    raise ExportError(f"Manifest publication failed ({exc.errno}); no snapshot was published.") from None
        try:
            _publish_directory(staged, destination)
        except Exception:
            if manifest is not None and manifest_identity is not None:
                try:
                    if manifest.lstat().st_ino == manifest_identity:
                        manifest.unlink()
                except OSError:
                    pass
            raise
    return initial


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1], help="Source root (default: this Prism checkout).")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Audit only; write no files.")
    action.add_argument("--out", type=Path, help="New snapshot directory; its parent must exist. Existing directories are never replaced.")
    parser.add_argument("--manifest", type=Path, help="Optional new local JSON manifest outside the snapshot; contains relative paths, sizes, and SHA-256 hashes.")
    arguments = parser.parse_args(argv)
    if arguments.check and arguments.manifest is not None:
        parser.error("--manifest requires --out")
    try:
        source = arguments.source.resolve()
        result = inventory(source) if arguments.check else export(source, arguments.out, arguments.manifest)
    except (ExportError, OSError) as exc:
        message = str(exc) if isinstance(exc, ExportError) else f"Filesystem operation failed ({exc.errno})."
        print(message, file=sys.stderr)
        return 1
    verb = "Audit passed" if arguments.check else "Snapshot exported"
    print(f"{verb}: {len(result.entries)} text files, {sum(entry.size for entry in result.entries)} bytes.")
    print("Excluded: " + ", ".join(f"{count} {rule}" for rule, count in sorted(result.exclusions.items())) + ".")
    print("Git history is excluded. Review the snapshot before publishing; pattern scanning cannot identify every private detail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
