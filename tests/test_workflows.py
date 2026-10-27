from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ("notes-latex", "reviewer-latex", "paper-latex")
INTERMEDIATES = {".aux", ".log", ".fls", ".fdb_latexmk", ".out", ".bbl", ".blg", ".toc", ".spl"}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.work = self.root / "build work"
        self.work.mkdir()
        self.bin = self.root / "commands"
        self.bin.mkdir()
        self.trace = self.root / "compiler calls.jsonl"
        self.env = os.environ.copy()
        self.env.update(
            PATH=str(self.bin),
            TMPDIR=str(self.work),
            PYTHONDONTWRITEBYTECODE="1",
            PRISM_TEST_LATEX_TRACE=str(self.trace),
        )
        for name in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
            self.env.pop(name, None)

    def run_cli(self, workflow: str, arguments: list[str], *, mode: str = "success"):
        env = self.env.copy()
        env["PRISM_TEST_LATEX_MODE"] = mode
        entrypoint = ROOT / "skills" / workflow / "scripts" / f"{workflow.replace('-', '_')}.py"
        return subprocess.run(
            [sys.executable, str(entrypoint), *arguments],
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=20,
        )

    def install_compiler(self):
        # The stub exercises CLI control flow and publication without requiring
        # TeX or rebuilding any user document. Real PDF smoke checks are separate.
        engine = self.bin / "xelatex"
        engine.write_text(f"#!{sys.executable}\n", encoding="utf-8")
        engine.chmod(0o755)
        compiler = self.bin / "latexmk"
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

    def make_source(self, workflow: str, *, suffix: str = ".md"):
        project = self.root / workflow
        project.mkdir(exist_ok=True)
        if workflow == "paper-latex":
            source = project / "main.tex"
            source.write_text(r"\documentclass{article}\begin{document}Test\end{document}", encoding="utf-8")
            return project, source, project / "main.pdf"
        source = project / f"draft{suffix}"
        fixture = ROOT / "tests/fixtures" / ("review.md" if workflow == "reviewer-latex" else "note.md")
        shutil.copy2(fixture, source)
        return source, source, project / "draft.pdf"

    def assert_no_intermediates(self, directory: Path):
        self.assertEqual(
            [path for path in directory.rglob("*") if path.is_file() and path.suffix in INTERMEDIATES],
            [],
        )

    def compiler_calls(self):
        if not self.trace.exists():
            return []
        return [json.loads(line) for line in self.trace.read_text(encoding="utf-8").splitlines()]

    def test_review_tex_export_persists_without_a_compiler(self):
        for layout in ("default", "outdir", "out-pdf", "out-tex"):
            with self.subTest(layout=layout):
                source_dir = self.root / layout
                source_dir.mkdir()
                source = source_dir / "review draft 中文.md"
                shutil.copy2(ROOT / "tests/fixtures/review.md", source)
                options = [str(source), "--no-compile", "--no-build-script"]
                if layout == "default":
                    author = source_dir / "review-draft.tex"
                elif layout == "outdir":
                    final_dir = self.root / "exported tex"
                    author = final_dir / "review-draft.tex"
                    options.extend(["--outdir", str(final_dir)])
                else:
                    requested = self.root / "explicit outputs" / ("author.tex" if layout == "out-tex" else "author.pdf")
                    author = requested.with_suffix(".tex")
                    options.extend(["--out", str(requested), "--outdir", str(self.root / "unused outdir")])
                result = self.run_cli("reviewer-latex", options)
                self.assertEqual(result.returncode, 0, result.stderr)
                editor = author.with_name(f"{author.stem}_editor_notes.tex")
                self.assertTrue(author.is_file(), result.stdout)
                self.assertTrue(editor.is_file(), result.stdout)
                self.assertNotIn("This sentence is confidential", author.read_text(encoding="utf-8"))
                self.assertIn("This sentence is confidential", editor.read_text(encoding="utf-8"))
                self.assertFalse(author.with_suffix(".pdf").exists())
                self.assertEqual(self.compiler_calls(), [])
                self.assertEqual(list(self.work.iterdir()), [])
                self.assert_no_intermediates(source_dir)

    def test_missing_engine_dependency_checks_report_all_missing_resources(self):
        for workflow in WORKFLOWS:
            for engine in ("auto", "xelatex"):
                with self.subTest(workflow=workflow, engine=engine):
                    result = self.run_cli(workflow, ["--check-deps", "--engine", engine])
                    self.assertEqual(result.returncode, 1, result.stderr)
                    for resource in ("latexmk", "kpsewhich", "xelatex", "geometry.sty", "texgyretermes-regular.otf", "FandolSong-Regular.otf"):
                        self.assertIn(f"{resource}: MISSING", result.stdout)
                    self.assertNotIn("Traceback", result.stderr)

    def test_compiler_failures_keep_existing_pdfs_and_clean_temporary_builds(self):
        self.install_compiler()
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow):
                cli_input, source, destination = self.make_source(workflow)
                before = source.read_bytes()
                destination.write_bytes(b"previous published PDF")
                result = self.run_cli(workflow, [str(cli_input), "--no-build-script"], mode="failure")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("deliberate compiler failure", result.stderr)
                self.assertEqual(destination.read_bytes(), b"previous published PDF")
                self.assertEqual(source.read_bytes(), before)
                self.assertEqual(list(self.work.iterdir()), [])
                self.assert_no_intermediates(source.parent)

    def test_renderer_failures_do_not_leak_work_directories(self):
        self.install_compiler()
        for workflow in ("notes-latex", "reviewer-latex"):
            with self.subTest(workflow=workflow):
                cli_input, source, destination = self.make_source(workflow, suffix=".csv")
                destination.write_bytes(b"previous published PDF")
                result = self.run_cli(workflow, [str(cli_input), "--no-build-script"])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Unsupported", result.stderr)
                self.assertEqual(destination.read_bytes(), b"previous published PDF")
                self.assertEqual(list(self.work.iterdir()), [])
                self.assert_no_intermediates(source.parent)

    def test_editor_compilation_failure_preserves_both_published_pdfs(self):
        self.install_compiler()
        cli_input, source, destination = self.make_source("reviewer-latex")
        editor = destination.with_name("draft_editor_notes.pdf")
        destination.write_bytes(b"previous author PDF")
        editor.write_bytes(b"previous confidential PDF")
        result = self.run_cli("reviewer-latex", [str(cli_input), "--no-build-script"], mode="editor-failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.compiler_calls()), 2)
        self.assertEqual(destination.read_bytes(), b"previous author PDF")
        self.assertEqual(editor.read_bytes(), b"previous confidential PDF")
        self.assertEqual(list(self.work.iterdir()), [])
        self.assert_no_intermediates(source.parent)

    def test_review_outdir_contains_final_pdfs_and_out_takes_precedence(self):
        self.install_compiler()
        cli_input, source, _ = self.make_source("reviewer-latex")
        final_dir = self.root / "published output"
        result = self.run_cli("reviewer-latex", [str(cli_input), "--outdir", str(final_dir), "--no-build-script"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({path.name for path in final_dir.iterdir()}, {"draft.pdf", "draft_editor_notes.pdf"})
        explicit = self.root / "custom" / "report.pdf"
        unused = self.root / "unused final dir"
        result = self.run_cli("reviewer-latex", [str(cli_input), "--outdir", str(unused), "--out", str(explicit), "--no-build-script"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(explicit.read_bytes(), b"new PDF from stub")
        self.assertEqual(explicit.with_name("report_editor_notes.pdf").read_bytes(), b"new PDF from stub")
        self.assertFalse((unused / "draft.pdf").exists())
        for call in self.compiler_calls():
            self.assertTrue(Path(call["outdir"]).is_relative_to(self.work))
            self.assertFalse(Path(call["outdir"]).exists())
        self.assertEqual(list(self.work.iterdir()), [])
        self.assert_no_intermediates(source.parent)

    def test_strict_layout_failure_does_not_replace_a_published_pdf(self):
        self.install_compiler()
        cli_input, source, destination = self.make_source("notes-latex")
        destination.write_bytes(b"previous PDF")
        result = self.run_cli("notes-latex", [str(cli_input), "--strict", "--no-build-script"], mode="strict-failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Strict LaTeX checks failed", result.stderr)
        self.assertEqual(destination.read_bytes(), b"previous PDF")
        self.assertEqual(list(self.work.iterdir()), [])
        self.assert_no_intermediates(source.parent)

    def test_keep_work_preserves_failed_build_and_reports_its_location(self):
        self.install_compiler()
        cli_input, _, _ = self.make_source("notes-latex")
        result = self.run_cli("notes-latex", [str(cli_input), "--keep-work", "--no-build-script"], mode="failure")
        self.assertNotEqual(result.returncode, 0)
        kept = list(self.work.iterdir())
        self.assertEqual(len(kept), 1)
        self.assertIn(str(kept[0]), result.stderr)
        self.assertTrue((kept[0] / "compile.log").is_file())

    def test_template_listing_and_invalid_initialization_options_need_no_compiler(self):
        result = self.run_cli("paper-latex", ["--list-templates"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prism:", result.stdout)
        self.assertIn("nature:", result.stdout)
        self.assertIn("bib: Briefings in Bioinformatics", result.stdout)
        self.assertIn("ddt: Drug Discovery Today", result.stdout)
        for arguments in (["--template", "nature"], ["--template-source", "offline.zip"], ["--init", str(self.root / "new"), "--template", "ddt", "--template-source", "offline.zip"], ["--force"], ["--list-templates", "--init", str(self.root / "new")], ["--init", str(self.root / "new"), "--check-deps"]):
            with self.subTest(arguments=arguments):
                result = self.run_cli("paper-latex", arguments)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / "new").exists())

    def test_marked_nature_project_auto_builds_with_pdflatex_and_preserves_cleanliness(self):
        self.install_compiler()
        (self.bin / "pdflatex").write_text(f"#!{sys.executable}\n")
        (self.bin / "pdflatex").chmod(0o755)
        cli_input, source, destination = self.make_source("paper-latex")
        (cli_input / "prism-template.json").write_text(json.dumps({"template": "nature", "prism_version": "2026.10.24", "engine": "pdflatex"}))
        result = self.run_cli("paper-latex", [str(cli_input), "--strict", "--no-build-script"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-pdf", self.compiler_calls()[0]["arguments"])
        self.assertEqual(destination.read_bytes(), b"new PDF from stub")
        self.assertEqual(list(self.work.iterdir()), [])
        self.assert_no_intermediates(cli_input)
        result = self.run_cli("paper-latex", [str(cli_input), "--engine", "xelatex", "--no-build-script"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nature template requires pdfLaTeX", result.stderr)
        self.assertEqual(len(self.compiler_calls()), 1)

    def test_marked_bib_project_uses_pdflatex_and_preserves_source_on_failure(self):
        self.install_compiler()
        (self.bin / "pdflatex").write_text(f"#!{sys.executable}\n")
        (self.bin / "pdflatex").chmod(0o755)
        cli_input, source, destination = self.make_source("paper-latex")
        original_source = source.read_bytes()
        (cli_input / "prism-template.json").write_text(json.dumps({"template": "bib", "engine": "pdflatex"}))
        result = self.run_cli("paper-latex", [str(cli_input), "--strict", "--no-build-script"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-pdf", self.compiler_calls()[0]["arguments"])
        self.assertEqual(destination.read_bytes(), b"new PDF from stub")
        result = self.run_cli("paper-latex", [str(cli_input), "--no-build-script"], mode="failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(destination.read_bytes(), b"new PDF from stub")
        self.assertEqual(source.read_bytes(), original_source)
        self.assertEqual(list(self.work.iterdir()), [])
        self.assert_no_intermediates(cli_input)

    def test_marked_ddt_project_uses_pdflatex_and_preserves_existing_output_on_failure(self):
        self.install_compiler()
        (self.bin / "pdflatex").write_text(f"#!{sys.executable}\n")
        (self.bin / "pdflatex").chmod(0o755)
        cli_input, source, destination = self.make_source("paper-latex")
        original_source = source.read_bytes()
        (cli_input / "prism-template.json").write_text(json.dumps({"template": "ddt", "engine": "pdflatex"}))
        result = self.run_cli("paper-latex", [str(cli_input), "--strict", "--no-build-script"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-pdf", self.compiler_calls()[0]["arguments"])
        self.assertEqual(destination.read_bytes(), b"new PDF from stub")
        result = self.run_cli("paper-latex", [str(cli_input), "--no-build-script"], mode="failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(destination.read_bytes(), b"new PDF from stub")
        self.assertEqual(source.read_bytes(), original_source)
        self.assertEqual(list(self.work.iterdir()), [])
        self.assert_no_intermediates(cli_input)

    def test_real_ddt_citations_and_spl_stay_out_of_source(self):
        for command in ("pdflatex", "latexmk", "bibtex", "kpsewhich", "pdftotext"):
            if not shutil.which(command):
                self.skipTest(f"Real DDT build needs {command}")
        for resource in ("elsarticle.cls", "elsarticle-num.bst"):
            check = subprocess.run(["kpsewhich", resource], capture_output=True, text=True, check=False)
            if check.returncode != 0 or not check.stdout.strip():
                self.skipTest(f"Real DDT build needs {resource}")
        project = self.root / "real DDT citation test"
        project.mkdir()
        (project / "main.tex").write_text(
            r"""\documentclass[review,12pt]{elsarticle}
\setcitestyle{super,sort&compress}
\begin{document}
\begin{frontmatter}\title{Citation test}\author{Example Author}\end{frontmatter}
First citation\cite{zulu2025}; second citation\cite{alpha2025}.
\bibliographystyle{elsarticle-num}
\bibliography{references}
\end{document}
""", encoding="utf-8",
        )
        (project / "references.bib").write_text(
            "@article{zulu2025,author={Zulu, Zoe},title={Synthetic Zulu reference},journal={Example Journal},year={2025}}\n"
            "@article{alpha2025,author={Alpha, Aaron},title={Synthetic Alpha reference},journal={Example Journal},year={2025}}\n",
            encoding="utf-8",
        )
        (project / "prism-template.json").write_text('{"template":"ddt","engine":"pdflatex"}', encoding="utf-8")
        env = os.environ.copy()
        env.update(TMPDIR=str(self.work), PYTHONDONTWRITEBYTECODE="1")
        for key in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
            env.pop(key, None)
        result = subprocess.run(
            [str(ROOT / "scripts" / "latex-paper.sh"), str(project), "--strict", "--no-build-script"],
            capture_output=True, text=True, check=False, env=env, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        extracted = subprocess.run(["pdftotext", "-raw", str(project / "main.pdf"), "-"], capture_output=True, text=True, check=True).stdout
        self.assertRegex(extracted, re.compile(r"First citation\s*(?:1|\[1\])\s*;", re.S))
        self.assertRegex(extracted, re.compile(r"second citation\s*(?:2|\[2\])\s*\.", re.S))
        self.assertLess(extracted.index("Zulu"), extracted.index("Alpha"))
        # System tools may create unrelated caches under TMPDIR (e.g. xcrun_db).
        self.assertEqual(list(self.work.glob("prism-paper-latex.*")), [])
        self.assert_no_intermediates(project)

    def test_paper_output_rejects_source_suffixes_and_symlink_aliases_before_compilation(self):
        self.install_compiler()
        cli_input, source, _ = self.make_source("paper-latex")
        originals = {source: source.read_bytes()}
        for name in ("sections/introduction.tex", "references.bib", "journal.bst", "prism-paper.sty", "journal.cls", "figure.png", "metadata.json", "README.md", "notes.txt", "analysis.py", "build.sh", "plain-text"):
            path = cli_input / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"original {name}".encode())
            originals[path] = path.read_bytes()
        for path in originals:
            with self.subTest(output=path):
                result = self.run_cli("paper-latex", [str(cli_input), "--out", str(path), "--no-build-script"])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(".pdf suffix", result.stderr)
                self.assertEqual(path.read_bytes(), originals[path])
                self.assertEqual(self.compiler_calls(), [])
        alias = cli_input / "out.pdf"
        alias.symlink_to("sections/introduction.tex")
        result = self.run_cli("paper-latex", [str(cli_input), "--out", str(alias), "--no-build-script"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved output path", result.stderr)
        self.assertTrue(alias.is_symlink())
        for path, content in originals.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual(self.compiler_calls(), [])
        self.assertEqual(list(self.work.iterdir()), [])
        default_output = cli_input / "main.pdf"
        default_output.symlink_to("main.tex")
        result = self.run_cli("paper-latex", [str(cli_input), "--no-build-script"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved output path", result.stderr)
        self.assertTrue(default_output.is_symlink())
        self.assertEqual(source.read_bytes(), originals[source])
        self.assertEqual(self.compiler_calls(), [])
        accepted = cli_input / "OUTPUT.PDF"
        result = self.run_cli("paper-latex", [str(cli_input), "--out", str(accepted), "--no-build-script"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(accepted.read_bytes(), b"new PDF from stub")

    def test_registered_paper_profiles_reject_incompatible_engines_for_builds_and_checks(self):
        self.install_compiler()
        cli_input, _, destination = self.make_source("paper-latex")
        destination.write_bytes(b"previous PDF")
        for template, engine in (("prism", "pdflatex"), ("nature", "xelatex"), ("nature", "lualatex"), ("bib", "xelatex"), ("bib", "lualatex"), ("ddt", "xelatex"), ("ddt", "lualatex")):
            with self.subTest(template=template, engine=engine):
                (cli_input / "prism-template.json").write_text(json.dumps({"template": template}))
                result = self.run_cli("paper-latex", [str(cli_input), "--engine", engine])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{template} template requires", result.stderr)
                result = self.run_cli("paper-latex", ["--check-deps", "--template", template, "--engine", engine])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{template} template requires", result.stderr)
        self.assertEqual(self.compiler_calls(), [])
        self.assertEqual(destination.read_bytes(), b"previous PDF")

    def test_unmarked_external_paper_retains_explicit_pdflatex_support(self):
        self.install_compiler()
        pdflatex = self.bin / "pdflatex"
        pdflatex.write_text(f"#!{sys.executable}\n")
        pdflatex.chmod(0o755)
        cli_input, _, destination = self.make_source("paper-latex")
        result = self.run_cli("paper-latex", [str(cli_input), "--engine", "pdflatex", "--no-build-script"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-pdf", self.compiler_calls()[0]["arguments"])
        self.assertEqual(destination.read_bytes(), b"new PDF from stub")

    def test_nature_dependency_profile_selects_pdflatex_and_checks_local_class(self):
        result = self.run_cli("paper-latex", ["--check-deps", "--template", "nature"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("pdflatex: MISSING", result.stdout)
        self.assertNotIn("fontspec", result.stdout)
        cli_input, _, _ = self.make_source("paper-latex")
        (cli_input / "prism-template.json").write_text('{"template":"nature"}')
        result = self.run_cli("paper-latex", [str(cli_input), "--check-deps"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("sn-jnl.cls: MISSING", result.stdout)
        self.assertIn("sn-nature.bst: MISSING", result.stdout)

    def test_bib_dependency_profile_checks_oup_packages_and_local_resources(self):
        result = self.run_cli("paper-latex", ["--check-deps", "--template", "bib"])
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("pdflatex: MISSING", result.stdout)
        self.assertIn("totcount.sty: MISSING", result.stdout)
        self.assertIn("tikz.sty: MISSING", result.stdout)
        self.assertIn("unsrt.bst: MISSING", result.stdout)
        self.assertNotIn("fontspec", result.stdout)
        cli_input, _, _ = self.make_source("paper-latex")
        (cli_input / "prism-template.json").write_text('{"template":"bib"}')
        result = self.run_cli("paper-latex", [str(cli_input), "--check-deps"])
        self.assertEqual(result.returncode, 1, result.stderr)
        for resource in ("oup-authoring-template.cls", "oup-plain.bst"):
            self.assertIn(f"{resource}: MISSING", result.stdout)
            (cli_input / resource).write_text("local upstream resource")
        result = self.run_cli("paper-latex", [str(cli_input), "--check-deps"])
        for resource in ("oup-authoring-template.cls", "oup-plain.bst"):
            self.assertIn(f"{resource}: {cli_input / resource}", result.stdout)
            self.assertNotIn(f"{resource}: MISSING", result.stdout)

    def test_ddt_dependency_profile_reports_missing_official_class_and_style(self):
        result = self.run_cli("paper-latex", ["--check-deps", "--template", "ddt"])
        self.assertEqual(result.returncode, 1, result.stderr)
        for resource in ("pdflatex", "elsarticle.cls", "elsarticle-num.bst"):
            self.assertIn(f"{resource}: MISSING", result.stdout)
        self.assertNotIn("fontspec", result.stdout)

    def test_paper_dependencies_require_bibtex_even_when_other_tools_are_available(self):
        self.install_compiler()
        (self.bin / "python3").symlink_to(sys.executable)
        for command in ("pdflatex", "kpsewhich"):
            executable = self.bin / command
            executable.write_text(f"#!{sys.executable}\nprint('/tex/resource')\n")
            executable.chmod(0o755)
        for template in ("prism", "nature", "bib", "ddt"):
            with self.subTest(template=template):
                result = self.run_cli("paper-latex", ["--check-deps", "--template", template])
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("bibtex: MISSING", result.stdout)
                self.assertEqual(result.stdout.count("MISSING"), 1)
        bibtex = self.bin / "bibtex"
        bibtex.write_text(f"#!{sys.executable}\n")
        bibtex.chmod(0o755)
        result = self.run_cli("paper-latex", ["--check-deps", "--template", "nature"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
