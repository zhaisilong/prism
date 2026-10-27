#!/usr/bin/env python3
"""Initialize or compile a portable academic LaTeX manuscript."""

from __future__ import annotations

import argparse
import os
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
    latexmk_command,
    project_version,
    warning_summary,
)
from build_script import write_build_script
from prism_latex.templates import (
    TEMPLATES,
    initialize,
    resolve_template,
    template_choices,
    template_engine,
    template_for_project,
    template_variant_for_project,
    template_isolated_build,
    template_packages,
    template_profile,
    template_resources,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--version", action="version", version=f"Prism {project_version()}")
    result.add_argument("paper_dir", nargs="?", type=Path, help="Directory containing the manuscript")
    result.add_argument("--init", metavar="TARGET_DIR", type=Path, help="Create a new manuscript project")
    result.add_argument("--list-templates", action="store_true", help="List available manuscript templates")
    result.add_argument("--template", choices=template_choices(), help="Template alias or stable ID for --init or --check-deps (default: prism)")
    result.add_argument("--template-source", metavar="PATH", type=Path, help="Explicit local official package/folder override; default initialization is offline")
    result.add_argument("--main", default="main.tex", help="Main TeX path relative to PAPER_DIR")
    result.add_argument("--out", type=Path, help="Output PDF path")
    result.add_argument("--engine", choices=("auto", "xelatex", "lualatex", "pdflatex"), default="auto")
    result.add_argument("--strict", action="store_true", help="Fail on missing glyphs, unresolved references, or overfull boxes")
    result.add_argument("--keep-work", action="store_true", help="Keep the temporary build directory")
    result.add_argument("--check-deps", action="store_true", help="Check required commands and TeX packages")
    result.add_argument("--force", action="store_true", help="Back up and replace an existing --init target")
    result.add_argument("--no-build-script", action="store_true", help="Do not create prism-build.sh after a successful build")
    result.add_argument("--force-build-script", action="store_true", help="Back up and replace a conflicting prism-build.sh")
    return result


def resolve_main(paper_dir: Path, relative: str) -> Path:
    root = paper_dir.expanduser().resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SystemExit("--main must stay inside PAPER_DIR.") from exc
    if not candidate.is_file():
        raise SystemExit(f"Main TeX file not found: {candidate}")
    return candidate


def main(argv: list[str] | None = None) -> int:
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if args.list_templates:
        if args.paper_dir or args.init or args.check_deps or args.template or args.template_source or args.force:
            argument_parser.error("--list-templates must be used without a project, initialization, or dependency options.")
        for name, details in TEMPLATES.items():
            publisher = details["publisher"] or "Prism"
            print(f"{name}: {details['description']} [ID: {details['id']}; type: {details['kind']}; publisher: {publisher}]")
        return 0
    if args.init and (args.paper_dir or args.check_deps):
        argument_parser.error("Use --init TARGET_DIR without PAPER_DIR or --check-deps.")
    if args.template and not (args.init or args.check_deps):
        argument_parser.error("--template is only supported with --init or --check-deps.")
    selected_template = resolve_template(args.template) if args.template else None
    if args.template_source and not (args.init and selected_template and template_profile(selected_template)["source"]):
        argument_parser.error("--template-source requires --init and a template that accepts an official source package.")
    if args.force and not args.init:
        argument_parser.error("--force requires --init TARGET_DIR.")
    if args.init:
        return initialize(args.init, args.force, selected_template or "prism", args.template_source)

    paper_dir = args.paper_dir.expanduser().resolve() if args.paper_dir else None
    if paper_dir is not None and not paper_dir.is_dir():
        raise SystemExit(f"Paper directory not found: {paper_dir}")
    template = selected_template or (template_for_project(paper_dir) if paper_dir else None)
    variant = template_variant_for_project(paper_dir) if paper_dir and not selected_template else None
    requested_engine = template_engine(template, args.engine)
    if args.check_deps:
        ok, rows = dependency_report(
            requested_engine, template_packages(template, requested_engine, variant),
        )
        bibtex = shutil.which("bibtex")
        rows.append(f"bibtex: {bibtex or 'MISSING'}")
        ok = ok and bool(bibtex)
        if paper_dir:
            for filename in template_resources(template, variant):
                exists = (paper_dir / filename).is_file()
                rows.append(f"{filename}: {paper_dir / filename if exists else 'MISSING'}")
                ok = ok and exists
        print("\n".join(rows))
        return 0 if ok else 1
    if paper_dir is None:
        raise SystemExit("PAPER_DIR is required unless --init, --list-templates, --version, or --check-deps is used.")

    main_path = resolve_main(paper_dir, args.main)
    destination = (args.out.expanduser() if args.out else paper_dir / f"{main_path.stem}.pdf").resolve()
    if destination.suffix.lower() != ".pdf":
        raise SystemExit("The resolved output path must have a .pdf suffix and must not replace a source file.")
    if destination == main_path:
        raise SystemExit("The output path must not replace the main TeX file.")
    engine = choose_engine(requested_engine)
    workdir = Path(tempfile.mkdtemp(prefix="prism-paper-latex."))
    relative_main = str(main_path.relative_to(paper_dir))

    env = os.environ.copy()
    search = str(paper_dir) + "//" + os.pathsep
    env["TEXINPUTS"] = search + env.get("TEXINPUTS", "")
    env["BIBINPUTS"] = search + env.get("BIBINPUTS", "")
    env["BSTINPUTS"] = search + env.get("BSTINPUTS", "")
    # achemso writes an acs-<jobname>.bib control file. BibTeX searches
    # its working directory before BIBINPUTS, so running from the source
    # directory can silently select a user's unrelated, same-named file.
    # Keep the normal working-directory behavior for other templates.
    isolate_cwd = template_isolated_build(template)
    build_cwd = workdir if isolate_cwd else paper_dir
    build_input = str(main_path) if isolate_cwd else relative_main
    try:
        result = subprocess.run(
            latexmk_command(engine, build_input, workdir),
            cwd=build_cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        (workdir / "compile.log").write_text(result.stdout, encoding="utf-8")
        if result.returncode != 0:
            tail = "\n".join(result.stdout.splitlines()[-100:])
            raise SystemExit(f"LaTeX compilation failed for {main_path}:\n{tail}")
        pdf = workdir / f"{main_path.stem}.pdf"
        if not pdf.exists():
            raise SystemExit(f"LaTeX finished but did not create {pdf}")
        final_log = (workdir / f"{main_path.stem}.log").read_text(encoding="utf-8", errors="replace")
        if args.strict:
            enforce_strict(final_log)
        warnings = warning_summary(final_log)
        if warnings:
            print("LaTeX warnings:\n" + "\n".join(warnings[:30]), file=sys.stderr)
        atomic_copy(pdf, destination)
        print(f"Wrote PDF: {destination}")
        if not args.no_build_script:
            script_options = ["--main", args.main, "--engine", args.engine]
            if args.strict:
                script_options.append("--strict")
            write_build_script(
                workflow="paper-latex",
                input_path=main_path,
                output_path=destination,
                project_dir=paper_dir,
                options=script_options,
                force=args.force_build_script,
            )
        return 0
    finally:
        if args.keep_work:
            print(f"Kept work directory: {workdir}", file=sys.stderr)
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
