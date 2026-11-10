"""Execute explicit LaTeX jobs and publish explicit artifacts.

Rendering and destination selection belong to the workflow adapters. Compilation
never publishes files; a batch is published only after every job has succeeded.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from .build_support import enforce_strict, latexmk_command, warning_summary


@dataclass(frozen=True)
class BuildJob:
    engine: str
    tex_input: str
    cwd: Path
    output_dir: Path
    env: Mapping[str, str] | None = None
    strict: bool = False
    compile_log: Path | None = None
    failure_context: str | None = None
    tail_lines: int = 80
    outdir_argument: bool = False

    def __post_init__(self) -> None:
        if not self.tex_input or self.tail_lines < 1:
            raise ValueError("A build needs a TeX input and a positive log-tail length.")
        if self.env is not None:
            object.__setattr__(self, "env", MappingProxyType(dict(self.env)))


@dataclass(frozen=True)
class BuildResult:
    pdf: Path
    log: str
    stdout: str
    warnings: tuple[str, ...]


def execute_build(job: BuildJob) -> BuildResult:
    """Compile one task and validate its result, without publishing anything."""
    result = subprocess.run(
        latexmk_command(
            job.engine, job.tex_input,
            job.output_dir if job.outdir_argument else None,
        ),
        cwd=job.cwd,
        env=job.env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if job.compile_log is not None:
        job.compile_log.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        tail = "\n".join(result.stdout.splitlines()[-job.tail_lines:])
        context = job.failure_context or str(job.cwd / job.tex_input)
        raise SystemExit(f"LaTeX compilation failed for {context}:\n{tail}")
    pdf = job.output_dir / f"{Path(job.tex_input).stem}.pdf"
    if not pdf.is_file():
        raise SystemExit(f"LaTeX finished but did not create {pdf}")
    log_path = pdf.with_suffix(".log")
    try:
        log = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SystemExit(f"Cannot read LaTeX log: {log_path}") from exc
    if job.strict:
        enforce_strict(log)
    return BuildResult(pdf, log, result.stdout, tuple(warning_summary(log)))


class Workspace:
    """Own temporary build directories while retaining explicitly chosen ones."""

    def __init__(self, prefix: str, path: Path | None = None, *, keep: bool = False):
        self.managed = path is None
        self.keep = keep
        self.path = (
            Path(tempfile.mkdtemp(prefix=prefix))
            if self.managed else path.expanduser().resolve()
        )
        self.path.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "Workspace":
        return self

    def __exit__(self, *exc_info) -> None:
        if self.managed and not self.keep:
            shutil.rmtree(self.path, ignore_errors=True)


@dataclass(frozen=True)
class Artifact:
    source: Path
    destination: Path


def _staging_file(destination: Path) -> Path:
    fd, filename = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent,
    )
    os.close(fd)
    return Path(filename)


def publish_artifacts(artifacts: Sequence[Artifact]) -> None:
    """Publish only named files, restoring old outputs if a replacement fails.

    Files and backups are staged beside each destination before any replacement.
    This protects ordinary I/O failures; it is not a cross-filesystem crash
    transaction. If rollback itself fails, its backup is retained for recovery.
    """
    batch = tuple(artifacts)
    destinations = [Path(os.path.abspath(item.destination)) for item in batch]
    if len(set(destinations)) != len(destinations):
        raise ValueError("Artifact destinations must be distinct.")
    sources = [Path(os.path.abspath(item.source)) for item in batch]
    if any(source in destinations for source in sources):
        raise ValueError("Published outputs must not replace artifact sources.")
    for source, destination in zip(sources, destinations):
        if not source.is_file():
            raise ValueError("Every artifact source must be an existing file.")
        if destination.exists() and not destination.is_file() and not destination.is_symlink():
            raise ValueError("An artifact destination must be a file path.")

    staged: list[Path] = []
    backups: list[Path | None] = []
    installed: list[int] = []
    retained: set[Path] = set()
    try:
        for source, destination in zip(sources, destinations):
            destination.parent.mkdir(parents=True, exist_ok=True)
            stage = _staging_file(destination)
            staged.append(stage)
            shutil.copy2(source, stage)
            backup = None
            if os.path.lexists(destination):
                backup = _staging_file(destination)
                backups.append(backup)
                # Preserve a destination symlink itself, including a dangling
                # link, rather than copying the data at its target.
                if destination.is_symlink():
                    backup.unlink()
                shutil.copy2(destination, backup, follow_symlinks=False)
            else:
                backups.append(None)
        for index, (stage, destination) in enumerate(zip(staged, destinations)):
            os.replace(stage, destination)
            installed.append(index)
    except BaseException as original:
        rollback_errors = []
        for index in reversed(installed):
            destination, backup = destinations[index], backups[index]
            try:
                if backup is None:
                    destination.unlink(missing_ok=True)
                else:
                    os.replace(backup, destination)
            except OSError:
                if backup is not None:
                    retained.add(backup)
                rollback_errors.append(str(destination))
        if rollback_errors:
            raise RuntimeError(
                "Artifact publication failed and some outputs could not be restored; "
                "recovery backups were retained beside: " + ", ".join(rollback_errors)
            ) from original
        raise
    finally:
        for temporary in (*staged, *(path for path in backups if path is not None)):
            if temporary not in retained:
                temporary.unlink(missing_ok=True)
