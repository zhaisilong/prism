"""Shared temporary environments and observable workflow checks."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "scripts/latex-paper.sh"
ENTRYPOINT = ROOT / "skills/paper-latex/scripts/paper_latex.py"
INTERMEDIATES = frozenset({".aux", ".bbl", ".bcf", ".blg", ".fdb_latexmk", ".fls",
                           ".log", ".out", ".spl", ".toc", ".lof", ".lot"})


def isolated_environment(temporary):
    env = os.environ.copy()
    env.update(TMPDIR=str(temporary), PYTHONDONTWRITEBYTECODE="1")
    for key in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
        env.pop(key, None)
    return env


def inventory(directory):
    return {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


def intermediates(directory):
    return sorted(path.relative_to(directory).as_posix() for path in directory.rglob("*")
                  if path.is_file() and path.suffix.lower() in INTERMEDIATES)


def pdf_text(pdf, mode="-layout"):
    return subprocess.run(["pdftotext", mode, str(pdf), "-"], capture_output=True,
                          text=True, check=True, timeout=30).stdout


def require_tex(case, resources=(), commands=("xelatex", "pdflatex", "latexmk", "bibtex", "kpsewhich", "pdftotext")):
    for command in commands:
        if not shutil.which(command):
            case.skipTest(f"Integration checks require {command}")
    for resource in resources:
        probe = subprocess.run(["kpsewhich", resource], capture_output=True, text=True, check=False)
        if probe.returncode or not probe.stdout.strip():
            case.skipTest(f"Integration checks require {resource}")


class TemplateSupport:
    """A test supplies its default alias; all fixtures remain synthetic."""

    default_template = "prism"

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="prism-template-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.env = isolated_environment(self.root)

    def cli(self, *arguments, env=None, timeout=180):
        command = [str(PAPER)] if env is None else [sys.executable, "-B", str(ENTRYPOINT)]
        return subprocess.run([*command, *map(str, arguments)], cwd=self.root,
                              env=self.env if env is None else env, capture_output=True,
                              text=True, check=False, timeout=timeout)

    def initialize(self, project, *, article_type=None, language="bilingual", force=False,
                   template=None, alias=None):
        from prism_latex import templates
        with contextlib.redirect_stdout(io.StringIO()):
            templates.initialize(project, force, alias or template or self.default_template,
                                 language=language, article_type=article_type)

    def assert_success(self, result, context=""):
        self.assertEqual(result.returncode, 0, context + "\n" + result.stdout + result.stderr)

    def inventory(self, directory):
        return inventory(directory)

    def assert_clean(self, directory):
        self.assertEqual(intermediates(directory), [])

    def text_of(self, pdf, mode="-layout"):
        return pdf_text(pdf, mode)


def install_fake_compiler(bin_dir):
    # The stub exercises CLI control flow and publication without requiring
    # TeX or rebuilding any user document. Real PDF smoke checks are separate.
    engine = bin_dir / "xelatex"
    engine.write_text(f"#!{sys.executable}\n", encoding="utf-8")
    engine.chmod(0o755)
    compiler = bin_dir / "latexmk"
    compiler.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "source = Path(sys.argv[-1])\n"
        "outdir = next((Path(arg.split('=', 1)[1]) for arg in sys.argv if arg.startswith('-outdir=')), Path.cwd())\n"
        "outdir.mkdir(parents=True, exist_ok=True)\n"
        "with open(os.environ['PRISM_TEST_LATEX_TRACE'], 'a', encoding='utf-8') as trace:\n"
        "    trace.write(json.dumps({'source': str(source), 'cwd': str(Path.cwd()), 'outdir': str(outdir), 'arguments': sys.argv[1:]}) + '\\n')\n"
        "(outdir / (source.stem + '.aux')).write_text('intermediate')\n"
        "mode = os.environ.get('PRISM_TEST_LATEX_MODE', 'success')\n"
        "if mode == 'failure' or (mode == 'editor-failure' and source.stem.endswith('_editor_notes')):\n"
        "    print('deliberate compiler failure')\n"
        "    sys.exit(42)\n"
        "log = 'Overfull \\\\hbox (5.0pt too wide)' if mode == 'strict-failure' else ''\n"
        "(outdir / (source.stem + '.log')).write_text(log)\n"
        "(outdir / (source.stem + '.pdf')).write_bytes(b'new PDF from stub')\n",
        encoding="utf-8",
    )
    compiler.chmod(0o755)
