from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib
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
        self.assertIn("nature-communications:", result.stdout)
        self.assertIn("bib: Briefings in Bioinformatics", result.stdout)
        self.assertIn("ddt: Drug Discovery Today", result.stdout)
        self.assertIn("jcim:", result.stdout)
        self.assertIn("science-advances:", result.stdout)
        for arguments in (["--template", "nature"], ["--template-source", "offline.zip"], ["--init", str(self.root / "new"), "--template", "ddt", "--template-source", "offline.zip"], ["--init", str(self.root / "new"), "--template", "jcim", "--template-source", "offline.zip"], ["--force"], ["--list-templates", "--init", str(self.root / "new")], ["--init", str(self.root / "new"), "--check-deps"]):
            with self.subTest(arguments=arguments):
                result = self.run_cli("paper-latex", arguments)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / "new").exists())

    def test_science_init_requires_source_before_creating_target(self):
        target = self.root / "new science parent" / "paper"
        result = self.run_cli("paper-latex", ["--init", str(target), "--template", "science-advances"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--template-source", result.stderr)
        self.assertFalse(target.parent.exists())

    def test_real_science_unifies_main_and_supplement_references(self):
        # The upstream source is intentionally not vendored. CI can opt in by
        # setting PRISM_SCIENCE_SOURCE to its own verified official directory.
        source = Path(os.environ.get("PRISM_SCIENCE_SOURCE", ROOT / "tmp" / "LaTeX_Template_for_Science_family_journals"))
        if not source.is_dir():
            self.skipTest("Real Science build needs PRISM_SCIENCE_SOURCE official directory")
        for command in ("pdflatex", "latexmk", "bibtex", "kpsewhich", "pdftotext"):
            if not shutil.which(command):
                self.skipTest(f"Real Science build needs {command}")
        for resource in ("newtxtext.sty", "newtxmath.sty"):
            check = subprocess.run(["kpsewhich", resource], capture_output=True, text=True, check=False)
            if check.returncode != 0 or not check.stdout.strip():
                self.skipTest(f"Real Science build needs {resource}")
        source_before = {name: (source / name).read_bytes() for name in ("scicite.sty", "sciencemag.bst", "readme.txt")}
        target = self.root / "论文 with spaces" / "Science Advances"
        env = os.environ.copy()
        env.update(TMPDIR=str(self.work), PYTHONDONTWRITEBYTECODE="1")
        for key in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
            env.pop(key, None)
        wrapper = str(ROOT / "scripts" / "latex-paper.sh")
        initialized = subprocess.run([wrapper, "--init", str(target), "--template", "science-advances", "--template-source", str(source)], capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        before = {path: path.read_bytes() for path in target.rglob("*") if path.is_file()}
        built = subprocess.run([wrapper, str(target), "--strict"], capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        pdf = target / "main.pdf"
        rebuild = target / "prism-build.sh"
        self.assertTrue(rebuild.is_file())
        extracted = subprocess.run(["pdftotext", "-raw", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        self.assertEqual(extracted.count("References and Notes"), 1)
        before_supplement, supplement = extracted.split("Supplementary Materials", 1)
        self.assertIn("Peng", before_supplement)
        self.assertIn("Sandve", before_supplement)
        self.assertLess(before_supplement.index("Peng"), before_supplement.index("Sandve"))
        self.assertRegex(supplement, re.compile(r"supplement-only example\s+citation\s*\(2\)", re.I))
        self.assertIn("Figure S1", extracted)
        self.assertIn("Table S1", extracted)
        self.assertIn("Equation S1", extracted)
        original_rebuild = rebuild.read_bytes()
        examples = subprocess.run([wrapper, str(target), "--main", "examples.tex", "--no-build-script", "--strict"], capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertEqual(examples.returncode, 0, examples.stdout + examples.stderr)
        self.assertTrue((target / "examples.pdf").is_file())
        self.assertEqual(rebuild.read_bytes(), original_rebuild)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        for name, content in source_before.items():
            self.assertEqual((source / name).read_bytes(), content)
        self.assert_no_intermediates(target)
        self.assertEqual(list(self.work.glob("prism-paper-latex.*")), [])

        archive_path = self.root / "official package.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            for path in source.iterdir():
                if path.is_file() and not path.is_symlink():
                    archive.write(path, f"science-family/{path.name}")
        zipped_target = self.root / "zip import"
        zipped = subprocess.run([wrapper, "--init", str(zipped_target), "--template", "science-advances", "--template-source", str(archive_path)], capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertEqual(zipped.returncode, 0, zipped.stdout + zipped.stderr)
        self.assertEqual((zipped_target / "scicite.sty").read_bytes(), source_before["scicite.sty"])
        self.assertEqual((zipped_target / "sciencemag.bst").read_bytes(), source_before["sciencemag.bst"])

        previous_pdf, previous_script = pdf.read_bytes(), rebuild.read_bytes()
        main_tex = target / "main.tex"
        main_tex.write_text(main_tex.read_text(encoding="utf-8").replace(r"\end{document}", r"Broken citation\cite{missing_fixture}." + "\n" + r"\end{document}"), encoding="utf-8")
        failed = subprocess.run([wrapper, str(target), "--strict"], capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertNotEqual(failed.returncode, 0, failed.stdout + failed.stderr)
        self.assertIn("missing_fixture", failed.stdout + failed.stderr)
        self.assertEqual(pdf.read_bytes(), previous_pdf)
        self.assertEqual(rebuild.read_bytes(), previous_script)
        self.assert_no_intermediates(target)

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

    def test_real_nature_communications_main_and_independent_supplement(self):
        for command in ("pdflatex", "latexmk", "bibtex", "kpsewhich", "pdftotext"):
            if not shutil.which(command):
                self.skipTest(f"Real Nature Communications build needs {command}")
        for resource in ("natbib.sty", "unsrt.bst", "siunitx.sty"):
            check = subprocess.run(["kpsewhich", resource], capture_output=True, text=True, check=False)
            if check.returncode != 0 or not check.stdout.strip():
                self.skipTest(f"Real Nature Communications build needs {resource}")
        project = self.root / "论文 with spaces" / "Nature Communications"
        env = os.environ.copy()
        env.update(TMPDIR=str(self.work), PYTHONDONTWRITEBYTECODE="1")
        for key in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
            env.pop(key, None)
        wrapper = str(ROOT / "scripts" / "latex-paper.sh")
        init = subprocess.run([wrapper, "--init", str(project), "--template", "nature-communications"], capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        before = {path: path.read_bytes() for path in project.rglob("*") if path.is_file()}
        main = subprocess.run([wrapper, str(project), "--strict"], capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertEqual(main.returncode, 0, main.stdout + main.stderr)
        script = project / "prism-build.sh"
        self.assertTrue(script.is_file())
        script_before = script.read_bytes()
        supplement = subprocess.run([wrapper, str(project), "--main", "supplementary.tex", "--no-build-script", "--strict"], capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertEqual(supplement.returncode, 0, supplement.stdout + supplement.stderr)
        self.assertEqual(script.read_bytes(), script_before)
        main_text = subprocess.run(["pdftotext", "-raw", str(project / "main.pdf"), "-"], capture_output=True, text=True, check=True).stdout
        supp_text = subprocess.run(["pdftotext", "-raw", str(project / "supplementary.pdf"), "-"], capture_output=True, text=True, check=True).stdout
        self.assertIn("fair guiding principles", main_text.lower())
        self.assertIn("fair guiding principles", supp_text.lower())
        self.assertIn("Supplementary Fig. 1", supp_text)
        self.assertIn("Supplementary Table 1", supp_text)
        self.assertIn("Supplementary Table 2", supp_text)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assert_no_intermediates(project)
        self.assertEqual(list(self.work.glob("prism-paper-latex.*")), [])

        # An unresolved reference must fail strict mode without replacing the
        # previously published PDF or the main project's rebuild script.
        pdf_before = (project / "main.pdf").read_bytes()
        main_tex = project / "main.tex"
        main_tex.write_text(main_tex.read_text(encoding="utf-8").replace(r"\end{document}", r"Broken citation\cite{missing_fixture}." + "\n" + r"\end{document}"), encoding="utf-8")
        failed = subprocess.run([wrapper, str(project), "--strict"], capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertNotEqual(failed.returncode, 0, failed.stdout + failed.stderr)
        self.assertIn("missing_fixture", failed.stdout + failed.stderr)
        self.assertEqual((project / "main.pdf").read_bytes(), pdf_before)
        self.assertEqual(script.read_bytes(), script_before)
        self.assert_no_intermediates(project)
        self.assertEqual(list(self.work.glob("prism-paper-latex.*")), [])

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

    def test_real_jcim_isolates_acs_control_bib_from_same_named_source(self):
        for command in ("pdflatex", "latexmk", "bibtex", "kpsewhich", "pdftotext"):
            if not shutil.which(command):
                self.skipTest(f"Real JCIM build needs {command}")
        for resource in ("achemso.sty", "achemso.bst", "xkeyval.sty", "natbib.sty", "natmove.sty"):
            check = subprocess.run(["kpsewhich", resource], capture_output=True, text=True, check=False)
            if check.returncode != 0 or not check.stdout.strip():
                self.skipTest(f"Real JCIM build needs {resource}")
        project = self.root / "JCIM citation test"
        (project / "sections").mkdir(parents=True)
        (project / "figures").mkdir()
        (project / "main.tex").write_text(
            r"""\documentclass[letterpaper]{article}
\usepackage[articletitle=true]{achemso}
\usepackage{graphicx}
\begin{document}
\input{sections/introduction}
\includegraphics[width=1cm]{figures/example.png}
\bibliography{references}
\end{document}
""", encoding="utf-8",
        )
        section = project / "sections" / "introduction.tex"
        section.write_text(r"First citation\cite{zulu2025}; second citation\cite{alpha2025}." + "\n", encoding="utf-8")
        (project / "references.bib").write_text(
            "@article{zulu2025,author={Zulu, Zoe},title={Synthetic Zulu reference},journal={Example Journal},year={2025}}\n"
            "@article{alpha2025,author={Alpha, Aaron},title={Synthetic Alpha reference},journal={Example Journal},year={2025}}\n",
            encoding="utf-8",
        )
        # Deliberately conflicting with the automatic package-generated file.
        # Preserving its bytes alone is not enough: BibTeX must not read it.
        sentinel = project / "acs-main.bib"
        sentinel.write_text(
            "@Control{achemso-control,ctrl-article-title={no}}\n"
            "@article{sentinel,author={Sentinel, Stella},title={Source-only sentinel},journal={Example},year={2025}}\n",
            encoding="utf-8",
        )
        (project / "prism-template.json").write_text('{"template":"jcim","engine":"pdflatex"}', encoding="utf-8")
        # One-pixel RGB PNG, created without nonstandard Python dependencies.
        def chunk(name, data):
            return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(b"\0\xff\xff\xff")) + chunk(b"IEND", b""))
        (project / "figures" / "example.png").write_bytes(png)
        before = {path: path.read_bytes() for path in project.rglob("*") if path.is_file()}
        env = os.environ.copy()
        env.update(TMPDIR=str(self.work), PYTHONDONTWRITEBYTECODE="1")
        for key in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
            env.pop(key, None)
        command = [str(ROOT / "scripts" / "latex-paper.sh"), str(project), "--strict", "--no-build-script"]
        result = subprocess.run(command, capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        pdf = project / "main.pdf"
        extracted = subprocess.run(["pdftotext", "-raw", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        # ACS natmove puts punctuation before the superscript citation.
        self.assertRegex(extracted, re.compile(r"First citation;\s*(?:1|\[1\])", re.S))
        self.assertRegex(extracted, re.compile(r"second citation\.\s*(?:2|\[2\])", re.S))
        self.assertLess(extracted.index("Zulu"), extracted.index("Alpha"))
        self.assertIn("Synthetic Zulu reference", extracted)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assert_no_intermediates(project)
        self.assertEqual(list(self.work.glob("prism-paper-latex.*")), [])

        # A source-only entry must remain unresolved and strict mode must retain
        # the previously published PDF, even when the conflicting file exists.
        previous_pdf = pdf.read_bytes()
        section.write_text(section.read_text(encoding="utf-8") + r"Unexpected \cite{sentinel}." + "\n", encoding="utf-8")
        result = subprocess.run(command, capture_output=True, text=True, check=False, env=env, timeout=120)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("sentinel", result.stdout + result.stderr)
        self.assertRegex(result.stdout + result.stderr, r"(?i)(?:undefined|didn't find a database entry)")
        self.assertEqual(pdf.read_bytes(), previous_pdf)
        self.assertEqual(sentinel.read_bytes(), before[sentinel])
        self.assert_no_intermediates(project)
        self.assertEqual(list(self.work.glob("prism-paper-latex.*")), [])

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
        for template, engine in (("prism", "pdflatex"), ("nature", "xelatex"), ("nature", "lualatex"), ("nature-communications", "xelatex"), ("nature-communications", "lualatex"), ("bib", "xelatex"), ("bib", "lualatex"), ("ddt", "xelatex"), ("ddt", "lualatex"), ("jcim", "xelatex"), ("jcim", "lualatex"), ("science-advances", "xelatex"), ("science-advances", "lualatex")):
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

    def test_jcim_dependency_profile_reports_missing_acs_resources(self):
        result = self.run_cli("paper-latex", ["--check-deps", "--template", "jcim"])
        self.assertEqual(result.returncode, 1, result.stderr)
        for resource in ("pdflatex", "achemso.sty", "achemso.bst", "natbib.sty", "natmove.sty", "xkeyval.sty"):
            self.assertIn(f"{resource}: MISSING", result.stdout)
        self.assertNotIn("fontspec", result.stdout)

    def test_nature_communications_dependency_profile_reports_missing_resources(self):
        result = self.run_cli("paper-latex", ["--check-deps", "--template", "nature-communications"])
        self.assertEqual(result.returncode, 1, result.stderr)
        for resource in ("pdflatex", "article.cls", "natbib.sty", "unsrt.bst"):
            self.assertIn(f"{resource}: MISSING", result.stdout)
        self.assertNotIn("fontspec", result.stdout)

    def test_science_dependency_profile_checks_local_styles(self):
        cli_input, _, _ = self.make_source("paper-latex")
        (cli_input / "prism-template.json").write_text('{"template":"science-advances"}')
        result = self.run_cli("paper-latex", [str(cli_input), "--check-deps"])
        self.assertEqual(result.returncode, 1, result.stderr)
        for resource in ("scicite.sty", "sciencemag.bst"):
            self.assertIn(f"{resource}: MISSING", result.stdout)
            (cli_input / resource).write_text("local synthetic resource")
        result = self.run_cli("paper-latex", [str(cli_input), "--check-deps"])
        for resource in ("scicite.sty", "sciencemag.bst"):
            self.assertIn(f"{resource}: {cli_input / resource}", result.stdout)
            self.assertNotIn(f"{resource}: MISSING", result.stdout)

    def test_paper_dependencies_require_bibtex_even_when_other_tools_are_available(self):
        self.install_compiler()
        (self.bin / "python3").symlink_to(sys.executable)
        for command in ("pdflatex", "kpsewhich"):
            executable = self.bin / command
            executable.write_text(f"#!{sys.executable}\nprint('/tex/resource')\n")
            executable.chmod(0o755)
        for template in ("prism", "nature", "nature-communications", "bib", "ddt", "jcim", "science-advances"):
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
