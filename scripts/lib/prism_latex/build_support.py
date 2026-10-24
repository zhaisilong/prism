#!/usr/bin/env python3
"""Shared dependency, font, and build helpers for Prism workflows."""

from __future__ import annotations

import datetime as dt
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ENGINES = ("xelatex", "lualatex")
SUPPORTED_ENGINES = (*ENGINES, "pdflatex")
COMMON_PACKAGES = (
    "geometry.sty", "fontspec.sty", "microtype.sty", "parskip.sty",
    "xcolor.sty", "hyperref.sty", "array.sty",
)
LATIN_FONTS = tuple(
    f"texgyre{family}-{style}.otf"
    for family in ("termes", "heros", "cursor")
    for style in ("regular", "bold", "italic", "bolditalic")
)
CJK_FONTS = (
    "FandolSong-Regular.otf", "FandolSong-Bold.otf",
    "FandolHei-Regular.otf", "FandolHei-Bold.otf", "FandolFang-Regular.otf",
)
STRICT_PATTERNS = (
    re.compile(r"Missing character:"),
    re.compile(r"(?:Citation|Reference) .+ undefined", re.IGNORECASE),
    re.compile(r"There were undefined references", re.IGNORECASE),
)
SUMMARY_PATTERNS = STRICT_PATTERNS + (
    re.compile(r"Overfull \\hbox"),
    re.compile(r"LaTeX Warning:"),
    re.compile(r"Package .+ Warning:"),
)


def project_version() -> str:
    path = Path(__file__).resolve().parents[3] / "VERSION"
    try:
        version = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SystemExit(f"Cannot read Prism version: {path}: {exc}") from exc
    if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}(?:\.[1-9]\d*)?", version):
        raise SystemExit(f"Invalid Prism version in {path}: expected YYYY.MM.DD or YYYY.MM.DD.N.")
    try:
        dt.date.fromisoformat(version[:10].replace(".", "-"))
    except ValueError as exc:
        raise SystemExit(f"Invalid calendar date in Prism version: {version}") from exc
    return version


def choose_engine(requested: str) -> str:
    if requested != "auto":
        if requested not in SUPPORTED_ENGINES:
            raise SystemExit(f"Unsupported engine: {requested}")
        if not shutil.which(requested):
            raise SystemExit(f"{requested} was not found on PATH.")
        return requested
    for engine in ENGINES:
        if shutil.which(engine):
            return engine
    raise SystemExit("Neither xelatex nor lualatex was found on PATH.")


def dependency_report(engine: str, packages: tuple[str, ...]) -> tuple[bool, list[str]]:
    if engine not in ("auto", *SUPPORTED_ENGINES):
        raise SystemExit(f"Unsupported engine: {engine}")
    available_engines = {name: shutil.which(name) for name in SUPPORTED_ENGINES}
    selected = (
        next((name for name in ENGINES if available_engines[name]), None)
        if engine == "auto" else engine
    )
    rows = [f"engine: {selected or 'MISSING (xelatex or lualatex)'}"]
    ok = bool(selected and available_engines[selected])
    commands = ("python3", "latexmk", selected) if selected else ("python3", "latexmk", *ENGINES)
    for command in commands:
        path = shutil.which(command)
        rows.append(f"{command}: {path or 'MISSING'}")
        ok = ok and bool(path)
    kpsewhich = shutil.which("kpsewhich")
    rows.append(f"kpsewhich: {kpsewhich or 'MISSING'}")
    ok = ok and bool(kpsewhich)
    cjk_packages = () if selected == "pdflatex" else (
        ("xeCJK.sty",) if selected == "xelatex"
        else ("luatexja-fontspec.sty",) if selected == "lualatex"
        else ("xeCJK.sty", "luatexja-fontspec.sty")
    )
    common = tuple(resource for resource in COMMON_PACKAGES if resource != "fontspec.sty") if selected == "pdflatex" else COMMON_PACKAGES
    fonts = () if selected == "pdflatex" else (*LATIN_FONTS, *CJK_FONTS)
    resources = tuple(dict.fromkeys((*common, *packages, *cjk_packages, *fonts)))
    for resource in resources:
        found = ""
        if kpsewhich:
            result = subprocess.run(
                [kpsewhich, resource], capture_output=True, text=True, check=False
            )
            found = result.stdout.strip() if result.returncode == 0 else ""
        rows.append(f"{resource}: {found or 'MISSING'}")
        ok = ok and bool(found)
    return ok, rows


def font_setup(engine: str, cjk: bool) -> str:
    latin = "\n".join(
        [
            r"\setmainfont{texgyretermes-regular.otf}[BoldFont=texgyretermes-bold.otf,ItalicFont=texgyretermes-italic.otf,BoldItalicFont=texgyretermes-bolditalic.otf]",
            r"\setsansfont{texgyreheros-regular.otf}[BoldFont=texgyreheros-bold.otf,ItalicFont=texgyreheros-italic.otf,BoldItalicFont=texgyreheros-bolditalic.otf]",
            r"\setmonofont{texgyrecursor-regular.otf}[BoldFont=texgyrecursor-bold.otf,ItalicFont=texgyrecursor-italic.otf,BoldItalicFont=texgyrecursor-bolditalic.otf]",
        ]
    )
    if not cjk:
        return latin
    if engine == "xelatex":
        return "\n".join(
            [
                latin,
                r"\usepackage{xeCJK}",
                r"\setCJKmainfont{FandolSong-Regular.otf}[BoldFont=FandolSong-Bold.otf]",
                r"\setCJKsansfont{FandolHei-Regular.otf}[BoldFont=FandolHei-Bold.otf]",
                r"\setCJKmonofont{FandolFang-Regular.otf}",
                r'\XeTeXlinebreaklocale "zh"',
                r"\XeTeXlinebreakskip=0pt plus 1pt",
            ]
        )
    return "\n".join(
        [
            latin,
            r"\usepackage{luatexja-fontspec}",
            r"\setmainjfont{FandolSong-Regular.otf}[BoldFont=FandolSong-Bold.otf]",
            r"\setsansjfont{FandolHei-Regular.otf}[BoldFont=FandolHei-Bold.otf]",
            r"\setmonojfont{FandolFang-Regular.otf}",
        ]
    )


def latexmk_command(engine: str, tex_name: str, outdir: Path | None = None) -> list[str]:
    modes = {"xelatex": "-xelatex", "lualatex": "-lualatex", "pdflatex": "-pdf"}
    if engine not in modes:
        raise SystemExit(f"Unsupported engine: {engine}")
    command = [
        "latexmk",
        modes[engine],
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
    ]
    if outdir is not None:
        command.append(f"-outdir={outdir}")
    command.append(tex_name)
    return command


def warning_summary(log_text: str) -> list[str]:
    found: list[str] = []
    for line in log_text.splitlines():
        compact = line.strip()
        if compact and any(pattern.search(compact) for pattern in SUMMARY_PATTERNS):
            if compact not in found:
                found.append(compact)
    return found


def enforce_strict(log_text: str) -> None:
    failures = [
        line.strip()
        for line in log_text.splitlines()
        if any(pattern.search(line) for pattern in STRICT_PATTERNS)
    ]
    for line in log_text.splitlines():
        match = re.search(r"Overfull \\hbox \(([0-9.]+)pt too wide\)", line)
        if match and float(match.group(1)) > 2.0:
            failures.append(line.strip())
    if failures:
        unique = list(dict.fromkeys(failures))
        raise SystemExit("Strict LaTeX checks failed:\n" + "\n".join(unique[:40]))


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temp_path = Path(temporary)
    try:
        shutil.copy2(source, temp_path)
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)
