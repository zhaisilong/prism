#!/usr/bin/env python3
"""Audit and export a fresh, text-only Prism code snapshot without Git history."""

from __future__ import annotations

import argparse
import collections
from contextlib import contextmanager
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from dataclasses import dataclass


ROOT_FILES = frozenset({".gitattributes", ".gitignore", "AGENTS.md", "CHANGELOG.md", "LICENSE", "README.md", "VERSION"})
SOURCE_DIRS = frozenset({"scripts", "skills", "tests", "docs"})
TEXT_SUFFIXES = frozenset({
    ".md", ".rst", ".txt", ".py", ".sh", ".tex", ".sty", ".bib", ".cls", ".bst",
    ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".csl", ".dtx", ".ins",
})
TEXT_NAMES = frozenset({"LICENSE", "NOTICE", "COPYING", "README", "Makefile", "VERSION", ".gitattributes", ".gitignore", ".gitkeep", ".latexmkrc"})
CACHE_DIRS = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache", ".tox",
    ".venv", "node_modules", "build", "dist", "out", "tmp", "temp",
})
GENERATED_SUFFIXES = frozenset({
    ".pyc", ".pyo", ".aux", ".bbl", ".bcf", ".blg", ".fdb_latexmk", ".fls",
    ".idx", ".ilg", ".ind", ".lof", ".log", ".lot", ".out", ".spl", ".toc",
})
METADATA_NAMES = frozenset({".git", ".hg", ".svn"})
MAX_TEXT_BYTES = 5 * 1024 * 1024
PUBLIC_FILE_LIST = "scripts/public-export-files.txt"

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

# Only these reviewed, byte-identical upstream notices may retain their
# published author/support email addresses. Never exempt an entire directory,
# accept a user-supplied manifest as an exemption, or skip credential/path scans.
UPSTREAM_NOTICE_SHA256 = {
    "skills/paper-latex/assets/upstream/oup/1.5/README":
        "3abf3f975cb4ecb6d02a0de30b3f72b59d7c7c496bf3e7111c3249e7586b7fe4",
    "skills/paper-latex/assets/upstream/oup/1.5/oup-abbrvnat.bst":
        "8004033e134786884125d7312a65f042d453c18f5970a54ecc193042904e00f9",
    "skills/paper-latex/assets/upstream/science/1.0/scicite.sty":
        "8030d7867d4094da12e59f3f0a6bc1d646d9c8454518872086d34bf25bbf2a99",
    "skills/paper-latex/assets/upstream/science/1.0/readme.txt":
        "a8ede7d50779a9f5e82f332780efeba5b6dba4b9cc04c87b1d0fd2464cc1cd9d",
}


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


@dataclass(frozen=True)
class ProtectedFile:
    # Local paths and hashes are deliberately absent from public records.
    path: Path
    sha256: str
    signature: tuple[int, ...]


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


def _privacy_rules(text: str, *, upstream_attribution: bool = False):
    rules = {name for name, pattern in PRIVATE_PATTERNS if pattern.search(text)}
    for match in EMAIL.finditer(text):
        domain = match.group(1).lower()
        if not upstream_attribution and not any(domain == allowed or domain.endswith("." + allowed) for allowed in EXAMPLE_DOMAINS):
            rules.add("non-example-email")
    return sorted(rules)


def _read_protected(path: Path) -> ProtectedFile:
    """Hash a private regular file without following any symbolic links."""
    path = path.absolute()
    descriptors = []
    try:
        current = os.open(path.anchor, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        descriptors.append(current)
        for part in path.parts[1:-1]:
            current = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                              | getattr(os, "O_NOFOLLOW", 0), dir_fd=current)
            descriptors.append(current)
        handle = os.open(path.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                         | getattr(os, "O_NONBLOCK", 0), dir_fd=current)
        descriptors.append(handle)
        before = os.fstat(handle)
        if not stat.S_ISREG(before.st_mode):
            raise ExportError("protected-file-not-regular")
        checksum = hashlib.sha256()
        total = 0
        with os.fdopen(os.dup(handle), "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                checksum.update(chunk)
                total += len(chunk)
        after = os.fstat(handle)
        if _signature(before) != _signature(after) or total != before.st_size:
            raise ExportError("protected-file-changed")
        return ProtectedFile(path, checksum.hexdigest(), _signature(after))
    except (OSError, ValueError):
        # Never include a private path, file name, contents, or hash in errors.
        raise ExportError("protected-file-unsafe-or-unreadable") from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _protected_inventory(paths):
    return tuple(_read_protected(Path(path)) for path in paths)


def _verify_protected(protected):
    for entry in protected:
        if _read_protected(entry.path) != entry:
            raise ExportError("protected-file-changed")


def _public_paths(source: Path):
    try:
        data, info = _read_regular(source, PUBLIC_FILE_LIST)
    except ExportError:
        raise ExportError(f"{PUBLIC_FILE_LIST}: unsafe-or-unreadable-file-list") from None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ExportError(f"{PUBLIC_FILE_LIST}: invalid-file-list-encoding") from None
    paths = set()
    for number, row in enumerate(text.splitlines(), 1):
        if not row.strip() or row.startswith("#"):
            continue
        path = PurePosixPath(row)
        if (row != row.strip() or path.is_absolute() or path.as_posix() != row
                or any(part in (".", "..") for part in path.parts)
                or any(char in row for char in "\\:*?[]{}")
                or any(ord(char) < 32 for char in row)
                or not (row in ROOT_FILES or row == "projects/.gitkeep"
                        or (len(path.parts) > 1 and path.parts[0] in SOURCE_DIRS))):
            raise ExportError(f"{PUBLIC_FILE_LIST}:{number}: invalid-public-file-path")
        if row in paths:
            raise ExportError(f"{PUBLIC_FILE_LIST}:{number}: duplicate-public-file-path")
        paths.add(row)
    if PUBLIC_FILE_LIST not in paths:
        raise ExportError(f"{PUBLIC_FILE_LIST}: file-list-must-include-itself")
    return paths, hashlib.sha256(data).hexdigest(), _signature(info)


@contextmanager
def _checked_directory(name, relative, *, parent_fd=None, expected=None):
    """Keep enumeration anchored to the checked directory, never its replacement."""
    descriptor = None
    try:
        if expected is None:
            expected = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                             dir_fd=parent_fd)
        if _signature(os.fstat(descriptor)) != _signature(expected):
            raise ExportError(f"{relative}: source-changed")
        yield descriptor
        if (_signature(os.fstat(descriptor)) != _signature(expected)
                or _signature(os.stat(name, dir_fd=parent_fd, follow_symlinks=False))
                != _signature(expected)):
            raise ExportError(f"{relative}: source-changed")
    except OSError as exc:
        raise ExportError(f"{relative}: unsafe-or-unreadable-directory ({exc.errno})") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _directory_names(descriptor, relative, expected):
    before = _signature(expected)
    if _signature(os.fstat(descriptor)) != before:
        raise ExportError(f"{relative}: source-changed")
    names = sorted(os.listdir(descriptor))
    if _signature(os.fstat(descriptor)) != before:
        raise ExportError(f"{relative}: source-changed")
    return names


def _inventory(source: Path, protected_hashes) -> Inventory:
    entries = []
    exclusions = collections.Counter()
    findings = []

    def inspect(parent_fd, name, relative, info):
        path = PurePosixPath(relative)
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
            with _checked_directory(name, relative, parent_fd=parent_fd, expected=info) as descriptor:
                for child in _directory_names(descriptor, relative, info):
                    child_relative = f"{relative}/{child}"
                    try:
                        child_info = os.stat(child, dir_fd=descriptor, follow_symlinks=False)
                    except OSError as exc:
                        raise ExportError(f"{child_relative}: unreadable-source ({exc.errno})") from None
                    inspect(descriptor, child, child_relative, child_info)
            return
        if not stat.S_ISREG(info.st_mode):
            findings.append(f"{relative}: non-regular-file")
            return
        if (path.name == ".DS_Store" or path.suffix.lower() in GENERATED_SUFFIXES
                or path.name.endswith((".run.xml", ".synctex.gz"))):
            exclusions["generated-files"] += 1
            return
        if relative not in public_paths:
            findings.append(f"{relative}: unreviewed-public-path")
            return
        if path.name not in ROOT_FILES | TEXT_NAMES and path.suffix.lower() not in TEXT_SUFFIXES:
            findings.append(f"{relative}: unrecognized-file-type")
            return
        if path.name.startswith(".") and path.name not in TEXT_NAMES:
            findings.append(f"{relative}: unrecognized-hidden-file")
            return
        data, opened = _read_regular(source, relative)
        digest = hashlib.sha256(data).hexdigest()
        if digest in protected_hashes:
            findings.append(f"{relative}: protected-content-match")
            return
        if relative == PUBLIC_FILE_LIST and (digest != list_hash or _signature(opened) != list_signature):
            raise ExportError(f"{PUBLIC_FILE_LIST}: source-changed")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(f"{relative}: binary-or-non-utf8-content")
            return
        if any(ord(char) < 32 and char not in "\t\r\n\f" for char in text):
            findings.append(f"{relative}: binary-control-characters")
            return
        approved_notice = UPSTREAM_NOTICE_SHA256.get(relative)
        if approved_notice and digest != approved_notice:
            findings.append(f"{relative}: upstream-notice-changed")
        for rule in _privacy_rules(text + "\n" + relative,
                                   upstream_attribution=approved_notice == digest):
            findings.append(f"{relative}: {rule}")
        entries.append(Entry(relative, len(data), digest,
                             0o755 if opened.st_mode & 0o111 else 0o644, _signature(opened)))

    with _checked_directory(source, ".") as root_fd:
        root_info = os.fstat(root_fd)
        public_paths, list_hash, list_signature = _public_paths(source)
        for name in _directory_names(root_fd, ".", root_info):
            if name not in ROOT_FILES | SOURCE_DIRS | {"projects"}:
                # Do not stat or traverse ignored or unrecognized root entries.
                exclusions["outside-allowlist-roots"] += 1
                continue
            try:
                info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            except OSError as exc:
                raise ExportError(f"{name}: unreadable-source ({exc.errno})") from None
            is_directory = stat.S_ISDIR(info.st_mode)
            is_link = stat.S_ISLNK(info.st_mode)
            if name in ROOT_FILES or name in SOURCE_DIRS:
                if name in ROOT_FILES and is_directory:
                    findings.append(f"{name}: expected-root-file")
                elif name in SOURCE_DIRS and not is_directory and not is_link:
                    findings.append(f"{name}: expected-source-directory")
                else:
                    inspect(root_fd, name, name, info)
            elif is_link:
                findings.append("projects: symlink")
            elif is_directory:
                with _checked_directory(name, "projects", parent_fd=root_fd, expected=info) as projects_fd:
                    try:
                        placeholder_info = os.stat(".gitkeep", dir_fd=projects_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        placeholder_info = None
                    if placeholder_info is not None:
                        if stat.S_ISDIR(placeholder_info.st_mode):
                            findings.append("projects/.gitkeep: expected-placeholder-file")
                        else:
                            inspect(projects_fd, ".gitkeep", "projects/.gitkeep", placeholder_info)
                exclusions["local-data-roots"] += 1
    missing = public_paths - {entry.path for entry in entries}
    findings.extend(f"{path}: reviewed-file-missing-or-rejected" for path in sorted(missing))
    data, info = _read_regular(source, PUBLIC_FILE_LIST)
    if hashlib.sha256(data).hexdigest() != list_hash or _signature(info) != list_signature:
        raise ExportError(f"{PUBLIC_FILE_LIST}: source-changed")
    if findings:
        raise ExportError("Audit failed:\n" + "\n".join(findings))
    if not entries:
        raise ExportError("No allowlisted source files found.")
    return Inventory(sorted(entries, key=lambda entry: entry.path), exclusions)


def inventory(source: Path, protect_files=()) -> Inventory:
    protected = _protected_inventory(protect_files)
    result = _inventory(source, {entry.sha256 for entry in protected})
    _verify_protected(protected)
    return result


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


def export(source: Path, destination: Path, manifest: Path | None = None, protect_files=()):
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
    protected = _protected_inventory(protect_files)
    protected_hashes = {entry.sha256 for entry in protected}
    initial = _inventory(source, protected_hashes)
    _verify_protected(protected)
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
        final = _inventory(source, protected_hashes)
        if initial.entries != final.entries:
            raise ExportError("Source changed during export; no snapshot was published.")
        _verify_protected(protected)
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
            _verify_protected(protected)
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
    parser.add_argument("--protect-file", type=Path, action="append", default=[],
                        help="Local private regular file whose complete contents must not be exported; repeatable. Paths and hashes are not recorded.")
    arguments = parser.parse_args(argv)
    if arguments.check and arguments.manifest is not None:
        parser.error("--manifest requires --out")
    try:
        source = arguments.source.resolve()
        result = (inventory(source, arguments.protect_file) if arguments.check
                  else export(source, arguments.out, arguments.manifest, arguments.protect_file))
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
