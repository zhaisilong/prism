#!/usr/bin/env python3
"""Install a small Codex paper-latex entry pointing to this Prism checkout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys
import tempfile


SKILL = "paper-latex"
MARKER = ".prism-paper-skill.json"
MANAGED_BY = "prism-paper-skill"


class InstallError(Exception):
    """An installation failed without replacing an unverified skill."""


def absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def reject_links(path: Path) -> None:
    for component in (path, *path.parents):
        if component.is_symlink():
            raise InstallError(f"Symbolic links are not supported in the installation path: {component}")


def choose_skills_dir(explicit: Path | None) -> Path:
    home = Path.home()
    candidates = [home / ".agents" / "skills", home / ".codex" / "skills"]
    if os.environ.get("CODEX_HOME"):
        candidates.append(Path(os.environ["CODEX_HOME"]) / "skills")
    candidates = list(dict.fromkeys(absolute(path) for path in candidates))
    existing = [path for path in candidates if os.path.lexists(path / SKILL)]
    if explicit is not None:
        selected = absolute(explicit)
        if not os.path.lexists(selected / SKILL) and existing:
            raise InstallError("A paper-latex entry already exists in a known skills directory; select that existing location with --skills-dir instead of creating a duplicate. No entries were changed.")
        return selected
    if len(existing) > 1:
        raise InstallError("Multiple paper-latex entries exist; select the intended location with --skills-dir. No entries were changed.")
    return existing[0] if existing else candidates[0]


def inventory(directory: Path) -> tuple | None:
    reject_links(directory)
    if not directory.exists():
        return None
    if not directory.is_dir():
        raise InstallError(f"The skill destination is not a directory: {directory}")
    rows = []
    for root, dirs, files in os.walk(directory, followlinks=False):
        for name in sorted((*dirs, *files)):
            path = Path(root) / name
            before = path.lstat()
            if stat.S_ISLNK(before.st_mode):
                raise InstallError("The existing skill contains a symbolic link; no files were changed.")
            digest = None
            if stat.S_ISREG(before.st_mode):
                with path.open("rb") as stream:
                    checksum = hashlib.sha256()
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        checksum.update(chunk)
                digest = checksum.hexdigest()
            elif not stat.S_ISDIR(before.st_mode):
                raise InstallError("The existing skill contains a special file; no files were changed.")
            after = path.lstat()
            signature = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if signature(before) != signature(after):
                raise InstallError("The existing skill changed during inspection; no files were changed.")
            rows.append((path.relative_to(directory).as_posix(), before.st_mode, before.st_size,
                         before.st_mtime_ns, before.st_ino, digest))
    info = directory.stat()
    return info.st_dev, info.st_ino, info.st_mode, tuple(sorted(rows))


def generated_files(repository: Path) -> dict[str, bytes]:
    command = (
        f"PRISM_REPO={shlex.quote(str(repository))}\n"
        'PRISM_REPO="${PRISM_PROJECT_DIR:-$PRISM_REPO}"\n'
        '"$PRISM_REPO/scripts/latex-paper.sh" --list-templates'
    )
    longest = max((len(run) for run in re.findall(r"`+", command)), default=0)
    fence = "`" * max(3, longest + 1)
    skill = f"""---
name: paper-latex
description: Initialize or compile academic LaTeX manuscripts with Prism journal templates, bibliography, figures, tables, equations, and supplementary material. Use for manuscript projects; route ordinary single-file notes to notes-latex.
---

# Paper LaTeX

Use the current Prism repository as the source of truth. The command below selects the installed checkout; `PRISM_PROJECT_DIR` can override it when the repository moves.

{fence}bash
{command}
{fence}

Read `skills/paper-latex/SKILL.md` in that repository before working and load its references only as needed. Run the repository's root wrappers by absolute path outside the checkout.

If the repository or wrapper is unavailable, report the missing location and ask for the current repository path. Do not fall back to old scripts or assets in this installed skill directory. Keep research files local and follow the repository's privacy and build rules.
"""
    interface = """interface:
  display_name: "Paper LaTeX"
  short_description: "Initialize and compile Prism journal manuscripts"
  default_prompt: "Use $paper-latex to initialize or compile my manuscript with Prism."
"""
    files = {"SKILL.md": skill.encode(), "agents/openai.yaml": interface.encode()}
    marker = {
        "schema_version": 1,
        "managed_by": MANAGED_BY,
        "repository": str(repository),
        "files_sha256": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
    }
    files[MARKER] = (json.dumps(marker, indent=2, ensure_ascii=False) + "\n").encode()
    return files


def is_managed(target: Path, repository: Path) -> bool:
    try:
        if (target / MARKER).is_file():
            marker = json.loads((target / MARKER).read_text(encoding="utf-8"))
            if not isinstance(marker, dict):
                return False
            expected = marker.get("files_sha256")
            return (type(marker.get("schema_version")) is int and marker["schema_version"] == 1
                    and marker.get("managed_by") == MANAGED_BY
                    and isinstance(expected, dict) and set(expected) == {"SKILL.md", "agents/openai.yaml"}
                    and all(hashlib.sha256((target / name).read_bytes()).hexdigest() == digest
                            for name, digest in expected.items()))
        text = (target / "SKILL.md").read_text(encoding="utf-8")
        # Recognize the earlier Prism router, which predates installation markers.
        return ("\nname: paper-latex\n" in text
                and "Use the current Prism repository as the source of truth for manuscript workflows." in text
                and f"otherwise use `{repository}`." in text
                and "Do not fall back to this skill directory's older scripts or assets." in text)
    except (OSError, ValueError, TypeError):
        return False


def backup_group(skills_dir: Path) -> Path:
    root = skills_dir.parent / "prism-skill-backups"
    reject_links(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    group = root / stamp
    group.mkdir(parents=True, exist_ok=False)
    return group


def install(repository: Path, skills_dir: Path | None = None, force: bool = False) -> tuple[Path, Path | None]:
    repository = repository.expanduser().resolve()
    required = ("skills/paper-latex/SKILL.md", "scripts/latex-paper.sh", "scripts/lib/prism_latex/templates.py")
    if any(not (repository / name).is_file() for name in required):
        raise InstallError("Install from a complete Prism checkout containing its skills and shared scripts.")
    skills_dir = choose_skills_dir(skills_dir)
    target = skills_dir / SKILL
    if repository == target or repository in target.parents or target in repository.parents:
        raise InstallError("The skill destination must be outside the Prism checkout.")
    reject_links(skills_dir)
    before = inventory(target)
    if before is not None and not force and not is_managed(target, repository):
        raise InstallError("An unrelated or edited paper-latex skill already exists. Use --force to back it up and replace it.")
    files = generated_files(repository)
    if before is not None and all((target / name).is_file() and (target / name).read_bytes() == content
                                  for name, content in files.items()) and len(before[3]) == 4:
        return target, None
    skills_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".prism-paper-stage-", dir=skills_dir.parent))
    backup = None
    published = False
    try:
        for name, content in files.items():
            output = stage / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
        if inventory(target) != before:
            raise InstallError("The existing skill changed during preparation; no files were replaced.")
        if before is not None:
            backup = backup_group(skills_dir) / SKILL
            target.rename(backup)
            if inventory(backup) != before:
                backup.rename(target)
                backup = None
                raise InstallError("The existing skill changed before backup; installation was stopped and the original was restored.")
        try:
            skills_dir.mkdir(parents=True, exist_ok=True)
            os.replace(stage, target)
            published = True
            if any((target / name).read_bytes() != content for name, content in files.items()):
                raise InstallError("The installed skill failed verification.")
        except (OSError, InstallError) as exc:
            failed = None
            if published and os.path.lexists(target):
                group = backup.parent if backup is not None else backup_group(skills_dir)
                failed = group / "failed-installation"
                target.rename(failed)
            if backup is not None and not os.path.lexists(target):
                backup.rename(target)
                backup = None
            if failed is not None:
                raise InstallError(f"Installation failed verification; the previous state was restored. Retained failed files: {failed}") from exc
            raise
        return target, backup
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, help="Codex skills directory (default: update an existing Prism entry, otherwise use the user .agents/skills directory)")
    parser.add_argument("--force", action="store_true", help="Back up and replace an unrelated or edited paper-latex entry")
    args = parser.parse_args(argv)
    try:
        target, backup = install(Path(__file__).resolve().parents[1], args.skills_dir, args.force)
    except (InstallError, OSError) as exc:
        print(f"Could not install paper-latex: {exc}", file=sys.stderr)
        return 1
    if backup is not None:
        print(f"Backed up previous skill: {backup}")
    print(f"Installed paper-latex: {target}")
    print("Codex detects skill changes automatically. Restart Codex if the updated entry does not appear.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
