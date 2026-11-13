#!/usr/bin/env python3
"""Initialize or compile a portable academic LaTeX manuscript."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from .build_support import (
    choose_engine,
    dependency_report,
    project_version,
)
from .build_script import write_build_script
from .runtime import Artifact, BuildJob, Workspace, execute_build, publish_artifacts
from .project import load_project_config
from .templates import (
    initialize,
    resolve_template,
    template_choices,
    template_engine,
    template_isolated_build,
    template_packages,
    template_profile,
    template_resources,
    template_article_type,
    article_type_choices,
    format_template_catalog,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--version", action="version", version=f"Prism {project_version()}")
    result.add_argument("paper_dir", nargs="?", type=Path, help="Directory containing the manuscript")
    result.add_argument("--init", metavar="TARGET_DIR", type=Path, help="Create a new manuscript project")
    result.add_argument("--list-templates", action="store_true", help="List available manuscript templates")
    result.add_argument("--group-by", choices=("none", "publisher"), help="Group --list-templates output (default: none)")
    result.add_argument("--template", choices=template_choices(), help="Template alias or stable ID for --init or --check-deps (default: prism)")
    result.add_argument("--article-type", choices=article_type_choices(), help="Content profile for multi-type templates, with --init or --check-deps; defaults are shown in the catalog")
    result.add_argument("--template-source", metavar="PATH", type=Path, help="Explicit local official package/folder override; default initialization is offline")
    result.add_argument("--language", choices=("bilingual", "english"), help="Language profile for initialization or dependency preview (default for new projects: bilingual)")
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
    if args.group_by is not None and not args.list_templates:
        argument_parser.error("--group-by requires --list-templates.")
    if args.list_templates:
        if args.paper_dir or args.init or args.check_deps or args.template or args.template_source or args.force or args.language or args.article_type:
            argument_parser.error("--list-templates must be used without a project, initialization, or dependency options.")
        print(format_template_catalog(args.group_by or "none"))
        return 0
    if args.init and (args.paper_dir or args.check_deps):
        argument_parser.error("Use --init TARGET_DIR without PAPER_DIR or --check-deps.")
    if args.template and not (args.init or args.check_deps):
        argument_parser.error("--template is only supported with --init or --check-deps.")
    if args.language and not (args.init or args.check_deps):
        argument_parser.error("--language is only supported with --init or --check-deps.")
    if args.article_type and not (args.init or args.check_deps):
        argument_parser.error("--article-type is only supported with --init or --check-deps.")
    selected_template = resolve_template(args.template) if args.template else None
    if args.template_source and not (args.init and selected_template and template_profile(selected_template)["source"]):
        argument_parser.error("--template-source requires --init and a template that accepts an official source package.")
    if args.force and not args.init:
        argument_parser.error("--force requires --init TARGET_DIR.")
    if args.init:
        init_template = selected_template or "prism"
        language = args.language or "bilingual"
        requested = template_engine(init_template, args.engine, language)
        default = template_engine(init_template, "auto", language)
        if args.engine != "auto" and default != "auto" and requested != default:
            argument_parser.error("--init selects its engine from --language; use --engine when building an existing project.")
        return initialize(args.init, args.force, init_template, args.template_source, language, args.article_type)

    paper_dir = args.paper_dir.expanduser().resolve() if args.paper_dir else None
    if paper_dir is not None and not paper_dir.is_dir():
        raise SystemExit(f"Paper directory not found: {paper_dir}")
    project = load_project_config(paper_dir) if paper_dir and not selected_template else None
    template = selected_template or (project.template if project else None)
    if args.check_deps and paper_dir is None and template is None:
        template = "prism"
    try:
        if args.article_type:
            template_article_type(template or "prism", args.article_type)
    except ValueError as exc:
        argument_parser.error(str(exc))
    variant = project.variant if project else None
    if args.language:
        language = args.language
    elif project:
        language = project.language
    else:
        language = "bilingual" if args.check_deps else None
    requested_engine = template_engine(template, args.engine, language)
    if args.check_deps:
        is_prism = not template or resolve_template(template) == "prism"
        ok, rows = dependency_report(
            requested_engine, template_packages(template, requested_engine, variant, language),
            include_latin_fonts=is_prism, include_cjk=is_prism or language == "bilingual",
        )
        bibtex = shutil.which("bibtex")
        rows.append(f"bibtex: {bibtex or 'MISSING'}")
        ok = ok and bool(bibtex)
        if paper_dir:
            for filename in template_resources(template, variant, language):
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
    relative_main = str(main_path.relative_to(paper_dir))

    env = os.environ.copy()
    search = str(paper_dir) + "//" + os.pathsep
    env["TEXINPUTS"] = search + env.get("TEXINPUTS", "")
    env["BIBINPUTS"] = search + env.get("BIBINPUTS", "")
    env["BSTINPUTS"] = search + env.get("BSTINPUTS", "")
    # achemso and rsc write per-job BibTeX control files. BibTeX searches
    # its working directory before BIBINPUTS, so use an isolated directory
    # to avoid writing or selecting unrelated files from the source project.
    isolate_cwd = template_isolated_build(template)
    workspace = Workspace(prefix="prism-paper-latex.", keep=args.keep_work)
    try:
        with workspace:
            workdir = workspace.path
            result = execute_build(BuildJob(
                engine=engine, tex_input=str(main_path) if isolate_cwd else relative_main,
                cwd=workdir if isolate_cwd else paper_dir, output_dir=workdir, env=env,
                strict=args.strict, compile_log=workdir / "compile.log",
                failure_context=str(main_path), tail_lines=100, outdir_argument=True,
            ))
            if result.warnings:
                print("LaTeX warnings:\n" + "\n".join(result.warnings[:30]), file=sys.stderr)
            publish_artifacts((Artifact(result.pdf, destination),))
            print(f"Wrote PDF: {destination}")
            if not args.no_build_script:
                script_options = ["--main", args.main, "--engine", args.engine]
                if args.strict:
                    script_options.append("--strict")
                legacy_xe_override = (
                    language is None and args.engine == "xelatex"
                    and os.path.lexists(paper_dir / "prism-build.sh")
                    and not args.force_build_script
                )
                if legacy_xe_override:
                    print("Warning: kept the existing prism-build.sh; use --force-build-script to update it for XeLaTeX.", file=sys.stderr)
                else:
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
            print(f"Kept work directory: {workspace.path}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
