#!/usr/bin/env python3
"""Render and compile a single note with the bundled Prism template."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from build_support import (
    atomic_copy,
    choose_engine,
    dependency_report,
    enforce_strict,
    font_setup as portable_font_setup,
    latexmk_command,
    project_version,
    warning_summary,
)
from build_script import write_build_script


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = SKILL_DIR / "assets" / "note_template.tex"

SUPERSCRIPT_MAP = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
    "⁺": "+",
    "⁻": "-",
    "⁽": "(",
    "⁾": ")",
    "ⁿ": "n",
    "˒": ",",
}

LATEX_ESCAPE = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

INLINE_PATTERNS = [
    ("link", re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")),
    ("code", re.compile(r"`([^`]+)`")),
    ("math", re.compile(r"\$\$[^$]+?\$\$|\$[^$\n]+?\$")),
    ("autocite", re.compile(r"\\(?:auto|paren|text)?cite\{[^}]+\}")),
    ("url", re.compile(r"https?://[^\s<>)\]]+")),
    ("bold", re.compile(r"\*\*([^*]+?)\*\*|__([^_]+?)__")),
]


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return normalize_input_text(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    return normalize_input_text(path.read_text(errors="replace"))


def format_timestamp(timestamp: float) -> str:
    return dt.date.fromtimestamp(timestamp).isoformat()


def file_created_date(path: Path) -> str:
    stat = path.stat()
    birthtime = getattr(stat, "st_birthtime", stat.st_ctime)
    return format_timestamp(birthtime)


def file_updated_date(path: Path) -> str:
    return format_timestamp(path.stat().st_mtime)


def normalize_input_text(text: str) -> str:
    return (
        text.replace("\ufeff", "")
        .replace("\ufffc", "")
        .replace("\x00", "")
        .replace("\xa0", " ")
    )


def has_cjk(text: str) -> bool:
    return any(
        "\u3400" <= char <= "\u4dbf"
        or "\u4e00" <= char <= "\u9fff"
        or "\uf900" <= char <= "\ufaff"
        for char in text
    )


def latex_escape(text: str) -> str:
    return "".join(LATEX_ESCAPE.get(char, char) for char in text)


def safe_url(url: str) -> str:
    return url.replace("\\", "/").replace("{", "%7B").replace("}", "%7D")


def render_codepath(text: str) -> str:
    break_after = set("/._-:=+,&;@#")
    output: list[str] = []
    for char in text:
        output.append(latex_escape(char))
        if char in break_after:
            output.append(r"\allowbreak{}")
    return r"\codepath{" + "".join(output) + "}"


def escape_text_segment(text: str) -> str:
    chars = "".join(re.escape(char) for char in SUPERSCRIPT_MAP)
    pattern = re.compile(f"([{chars}]+)")
    output: list[str] = []
    pos = 0
    for match in pattern.finditer(text):
        output.append(latex_escape(text[pos : match.start()]))
        converted = "".join(SUPERSCRIPT_MAP.get(char, "") for char in match.group(1))
        if converted:
            output.append(r"\textsuperscript{" + latex_escape(converted) + "}")
        pos = match.end()
    output.append(latex_escape(text[pos:]))
    return "".join(output)


def escape_table_text_segment(text: str) -> str:
    break_after = set("_/")
    output: list[str] = []
    for index, char in enumerate(text):
        output.append(LATEX_ESCAPE.get(char, char))
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if char in break_after or (char == "-" and not next_char.isdigit()):
            output.append(r"\allowbreak{}")
    return "".join(output)


def render_inline(text: str) -> str:
    return render_inline_with_escaper(text, escape_text_segment)


def render_table_inline(text: str) -> str:
    return render_inline_with_escaper(text, escape_table_text_segment)


def render_inline_with_escaper(text: str, escaper) -> str:
    output: list[str] = []
    pos = 0
    while pos < len(text):
        earliest: tuple[int, int, str, re.Match[str]] | None = None
        for kind, pattern in INLINE_PATTERNS:
            match = pattern.search(text, pos)
            if not match:
                continue
            candidate = (match.start(), match.end(), kind, match)
            if earliest is None or candidate[0] < earliest[0]:
                earliest = candidate

        if earliest is None:
            output.append(escaper(text[pos:]))
            break

        start, end, kind, match = earliest
        output.append(escaper(text[pos:start]))

        token = match.group(0)
        if kind == "link":
            label = render_inline_with_escaper(match.group(1), escaper)
            output.append(r"\href{" + safe_url(match.group(2)) + "}{" + label + "}")
        elif kind == "code":
            output.append(render_codepath(match.group(1)))
        elif kind == "math":
            output.append(token)
        elif kind == "autocite":
            output.append(token)
        elif kind == "url":
            output.append(r"\url{" + safe_url(token) + "}")
        elif kind == "bold":
            inner = match.group(1) or match.group(2) or ""
            output.append(r"\textbf{" + render_inline_with_escaper(inner, escaper) + "}")
        pos = end
    return "".join(output)


def split_pipe_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_pipe_separator(line: str) -> bool:
    cells = split_pipe_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def is_pipe_table_start(lines: list[str], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and "|" in lines[index]
        and "|" in lines[index + 1]
        and is_pipe_separator(lines[index + 1])
    )


def render_pipe_table(lines: list[str], index: int) -> tuple[str, int]:
    header = split_pipe_row(lines[index])
    rows: list[list[str]] = []
    i = index + 2
    while i < len(lines) and "|" in lines[i].strip() and lines[i].strip():
        rows.append(split_pipe_row(lines[i]))
        i += 1

    column_count = max([len(header)] + [len(row) for row in rows])
    header = (header + [""] * column_count)[:column_count]
    normalized_rows = [(row + [""] * column_count)[:column_count] for row in rows]
    column_spec = table_column_spec(column_count)
    table_font = r"\scriptsize" if column_count >= 8 else r"\footnotesize" if column_count >= 6 else r"\small"
    table_colsep = "2pt" if column_count >= 6 else "4pt"

    if len(normalized_rows) >= 20 and column_count <= 5:
        width = 0.94 / column_count
        long_spec = "".join(rf"P{{{width:.3f}\linewidth}}" for _ in range(column_count))
        header_line = " & ".join(
            r"\textbf{" + render_table_inline(cell) + "}" for cell in header
        ) + r" \\"
        output = [
            table_font,
            rf"\setlength{{\tabcolsep}}{{{table_colsep}}}",
            rf"\begin{{longtable}}{{@{{}}{long_spec}@{{}}}}",
            r"\toprule",
            header_line,
            r"\midrule",
            r"\endfirsthead",
            r"\toprule",
            header_line,
            r"\midrule",
            r"\endhead",
        ]
        for row in normalized_rows:
            output.append(" & ".join(render_table_inline(cell) for cell in row) + r" \\")
        output.extend([r"\bottomrule", r"\end{longtable}"])
        return "\n".join(output), i

    output = [
        r"\begin{center}",
        table_font,
        rf"\setlength{{\tabcolsep}}{{{table_colsep}}}",
        rf"\begin{{tabularx}}{{\linewidth}}{{@{{}}{column_spec}@{{}}}}",
        r"\toprule",
        " & ".join(r"\textbf{" + render_table_inline(cell) + "}" for cell in header) + r" \\",
        r"\midrule",
    ]
    for row in normalized_rows:
        output.append(" & ".join(render_table_inline(cell) for cell in row) + r" \\")
    output.extend([r"\bottomrule", r"\end{tabularx}", r"\end{center}"])
    return "\n".join(output), i


def table_column_spec(column_count: int) -> str:
    if column_count <= 1:
        return "Y"
    if column_count == 2:
        return r"P{0.32\linewidth}Y"
    if column_count == 3:
        return r"P{0.24\linewidth}YY"
    if column_count == 6:
        return r"P{0.08\linewidth}P{0.23\linewidth}YYYY"
    if column_count >= 8:
        return r"P{0.10\linewidth}P{0.07\linewidth}" + "Y" * (column_count - 2)
    return r"P{0.20\linewidth}" + "Y" * (column_count - 1)


def markdown_heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def tex_heading(line: str) -> str | None:
    match = re.match(r"^\s*\\(section|subsection|subsubsection)\*?\{(.+)\}\s*$", line)
    if not match:
        return None
    command = {
        "section": "tightsection",
        "subsection": "tightsubsection",
        "subsubsection": "tightsubsubsection",
    }[match.group(1)]
    return rf"\{command}{{{render_inline(match.group(2))}}}"


def is_list_item(line: str) -> tuple[str, str, str | None] | None:
    stripped = line.strip()
    unordered = re.match(r"^[-*+]\s+(.+)$", stripped)
    if unordered:
        return "itemize", unordered.group(1), None
    ordered = re.match(r"^(\d+)([.)])\s+(.+)$", stripped)
    if ordered:
        return "enumerate", ordered.group(3), ordered.group(1) + ordered.group(2)
    return None


def is_horizontal_rule(line: str) -> bool:
    return bool(re.fullmatch(r"\s*(-{3,}|\*{3,}|_{3,})\s*", line))


def blockquote_content(line: str) -> str | None:
    match = re.match(r"^\s*>\s?(.*)$", line)
    if not match:
        return None
    return match.group(1)


def is_block_start(lines: list[str], index: int) -> bool:
    line = lines[index]
    return bool(
        not line.strip()
        or line.strip().startswith("```")
        or markdown_heading(line)
        or tex_heading(line)
        or is_list_item(line)
        or is_horizontal_rule(line)
        or blockquote_content(line) is not None
        or is_pipe_table_start(lines, index)
    )


def render_note_blocks(text: str, skip_first_h1: bool = False) -> str:
    lines = text.splitlines()
    output: list[str] = []
    list_state: str | None = None
    i = 0
    skipped_h1 = False

    def close_list() -> None:
        nonlocal list_state
        if list_state:
            output.append(rf"\end{{{list_state}}}")
            list_state = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            close_list()
            i += 1
            continue

        if stripped.startswith("```"):
            close_list()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            output.append(r"\begin{verbatim}")
            output.extend(code_lines)
            output.append(r"\end{verbatim}")
            continue

        if is_pipe_table_start(lines, i):
            close_list()
            table, i = render_pipe_table(lines, i)
            output.append(table)
            continue

        heading = markdown_heading(line)
        if heading:
            close_list()
            level, title = heading
            if skip_first_h1 and level == 1 and not skipped_h1:
                skipped_h1 = True
                i += 1
                continue
            command = "tightsection" if level <= 2 else "tightsubsection" if level == 3 else "tightsubsubsection"
            output.append(rf"\{command}{{{render_inline(title)}}}")
            i += 1
            continue

        rendered_tex_heading = tex_heading(line)
        if rendered_tex_heading:
            close_list()
            output.append(rendered_tex_heading)
            i += 1
            continue

        if is_horizontal_rule(line):
            close_list()
            i += 1
            continue

        quote_line = blockquote_content(line)
        if quote_line is not None:
            close_list()
            quote_lines: list[str] = []
            while i < len(lines):
                quote_line = blockquote_content(lines[i])
                if quote_line is None:
                    break
                quote_lines.append(quote_line)
                i += 1
            quote_body = render_note_blocks("\n".join(quote_lines))
            output.append(r"\begin{quote}" + "\n" + (quote_body or r"\strut") + "\n" + r"\end{quote}")
            continue

        list_item = is_list_item(line)
        if list_item:
            env, item_text, item_marker = list_item
            if list_state != env:
                close_list()
                output.append(rf"\begin{{{env}}}")
                list_state = env
            if item_marker:
                output.append(r"\item[" + latex_escape(item_marker) + "] " + render_inline(item_text))
            else:
                output.append(r"\item " + render_inline(item_text))
            i += 1
            continue

        close_list()
        paragraph = [stripped]
        i += 1
        while i < len(lines) and not is_block_start(lines, i):
            paragraph.append(lines[i].strip())
            i += 1
        output.append(render_inline(" ".join(paragraph)))

    close_list()
    return "\n\n".join(output).strip()


def parse_date_line(line: str) -> tuple[str, str] | None:
    raw = line.strip()
    match = re.match(
        r"^(?:[-*]\s*)?(创建日期|创建时间|created|created date|更新日期|更新时间|updated|updated date)\s*[:：]\s*(.+?)\s*$",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    label = match.group(1).lower()
    kind = "created" if label in {"创建日期", "创建时间", "created", "created date"} else "updated"
    value = match.group(2).strip()
    date_match = re.search(r"\d{4}-\d{1,2}-\d{1,2}", value)
    if date_match:
        value = date_match.group(0)
    return kind, value


def extract_note_dates(text: str) -> tuple[str, str, str]:
    created = ""
    updated = ""
    kept_lines: list[str] = []
    for line in text.splitlines():
        parsed = parse_date_line(line)
        if parsed:
            kind, value = parsed
            if kind == "created" and not created:
                created = value
            elif kind == "updated" and not updated:
                updated = value
            continue
        kept_lines.append(line)
    return created, updated, "\n".join(kept_lines)


def infer_title(path: Path, text: str, override: str | None) -> tuple[str, bool]:
    if override:
        return override, False
    for line in text.splitlines():
        heading = markdown_heading(line)
        if heading and heading[0] == 1:
            return heading[1], True
    stem = path.stem.replace("_", " ").replace("-", " ").strip()
    if stem.isalpha() and len(stem) <= 4:
        return stem.upper(), False
    return stem.title(), False


def render_wrapped_document(
    source: Path,
    text: str,
    title_override: str | None,
    created_date: str | None,
    updated_date: str | None,
    engine: str = "xelatex",
) -> str:
    extracted_created, extracted_updated, content_text = extract_note_dates(text)
    created = created_date or extracted_created or file_created_date(source)
    updated = updated_date or extracted_updated or file_updated_date(source)
    title, skip_first_h1 = infer_title(source, content_text, title_override)
    body = render_note_blocks(content_text, skip_first_h1=skip_first_h1)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "<<FONT_SETUP>>": portable_font_setup(engine, has_cjk(text)),
        "<<PDF_TITLE>>": escape_text_segment(title),
        "<<TITLE>>": render_inline(title),
        "<<META>>": render_inline(f"创建日期：{created}；更新日期：{updated}"),
        "<<BODY>>": body or r"\textit{No content.}",
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def render_source(
    source: Path,
    title: str | None,
    created_date: str | None,
    updated_date: str | None,
    engine: str = "xelatex",
) -> str:
    text = read_text(source)
    if source.suffix.lower() == ".tex" and re.search(r"\\documentclass(?:\[[^\]]+\])?\{", text):
        return text
    if source.suffix.lower() not in {".md", ".txt", ".tex"}:
        raise SystemExit(f"Unsupported note type: {source.suffix}. Use .md, .txt, or .tex.")
    return render_wrapped_document(source, text, title, created_date, updated_date, engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"Prism {project_version()}")
    parser.add_argument("source", nargs="?", type=Path, help="Source .md, .txt, or .tex note")
    parser.add_argument("--workdir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--out", type=Path, help="Output PDF path; defaults beside the source")
    parser.add_argument("--title", help="Override the rendered note title")
    parser.add_argument("--created-date", help="Override the rendered creation date")
    parser.add_argument("--updated-date", help="Override the rendered update date")
    parser.add_argument("--date", help="Backward-compatible alias for --updated-date")
    parser.add_argument("--engine", choices=("auto", "xelatex", "lualatex"), default="auto")
    parser.add_argument("--strict", action="store_true", help="Fail on missing glyphs, unresolved references, or overfull boxes")
    parser.add_argument("--keep-work", action="store_true", help="Keep the temporary build directory")
    parser.add_argument("--check-deps", action="store_true", help="Check required commands and TeX packages, then exit")
    parser.add_argument("--no-build-script", action="store_true", help="Do not create prism-build.sh after a successful build")
    parser.add_argument("--force-build-script", action="store_true", help="Back up and replace a conflicting prism-build.sh")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check_deps:
        ok, rows = dependency_report(
            args.engine,
            ("tabularx.sty", "booktabs.sty", "longtable.sty", "amsmath.sty", "amssymb.sty"),
        )
        print("\n".join(rows))
        return 0 if ok else 1
    if args.source is None:
        raise SystemExit("SOURCE is required unless --check-deps is used.")

    source = args.source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Source not found: {source}")
    if not source.is_file():
        raise SystemExit(f"Source is not a file: {source}")

    engine = choose_engine(args.engine)
    destination = args.out.expanduser().resolve() if args.out else source.with_suffix(".pdf")
    if destination == source:
        raise SystemExit("The output path must not replace the source file.")
    managed_workdir = args.workdir is None
    workdir = (
        Path(tempfile.mkdtemp(prefix="prism-notes-latex."))
        if managed_workdir
        else args.workdir.expanduser().resolve()
    )
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        updated_date = args.updated_date or args.date
        tex = render_source(source, args.title, args.created_date, updated_date, engine)
        output = workdir / "main.tex"
        output.write_text(tex, encoding="utf-8")
        env = os.environ.copy()
        search = str(source.parent) + "//" + os.pathsep
        for variable in ("TEXINPUTS", "BIBINPUTS", "BSTINPUTS"):
            env[variable] = search + env.get(variable, "")
        result = subprocess.run(
            latexmk_command(engine, output.name),
            cwd=workdir,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        (workdir / "compile.log").write_text(result.stdout, encoding="utf-8")
        if result.returncode != 0:
            tail = "\n".join(result.stdout.splitlines()[-80:])
            raise SystemExit(f"LaTeX compilation failed for {source}:\n{tail}")
        pdf = workdir / "main.pdf"
        if not pdf.exists():
            raise SystemExit(f"LaTeX finished but did not create {pdf}")
        final_log = (workdir / "main.log").read_text(encoding="utf-8", errors="replace")
        if args.strict:
            enforce_strict(final_log)
        warnings = warning_summary(final_log)
        if warnings:
            print("LaTeX warnings:", file=sys.stderr)
            print("\n".join(warnings[:20]), file=sys.stderr)
        atomic_copy(pdf, destination)
        print(f"Wrote PDF: {destination}")
        if not args.no_build_script:
            script_options = ["--engine", args.engine]
            if args.title is not None:
                script_options.extend(["--title", args.title])
            if args.created_date is not None:
                script_options.extend(["--created-date", args.created_date])
            if updated_date is not None:
                script_options.extend(["--updated-date", updated_date])
            if args.strict:
                script_options.append("--strict")
            write_build_script(
                workflow="notes-latex",
                input_path=source,
                output_path=destination,
                project_dir=source.parent,
                options=script_options,
                force=args.force_build_script,
            )
        return 0
    finally:
        if managed_workdir and not args.keep_work:
            shutil.rmtree(workdir, ignore_errors=True)
        elif args.keep_work:
            print(f"Kept work directory: {workdir}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
