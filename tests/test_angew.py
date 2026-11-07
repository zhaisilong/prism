from __future__ import annotations

import concurrent.futures
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from prism_latex import templates

PAPER = ROOT / "scripts" / "latex-paper.sh"
ENTRYPOINT = ROOT / "skills" / "paper-latex" / "scripts" / "paper_latex.py"
ARTICLE_TYPES = ("research", "communication", "review", "minireview")
INTERMEDIATES = {".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".log", ".out", ".spl", ".toc"}


class AngewSupport:
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="prism-angew-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.env = os.environ.copy()
        self.env.update(PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(self.root))
        for key in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
            self.env.pop(key, None)

    def cli(self, *args, env=None, timeout=180):
        command = [str(PAPER)] if env is None else [sys.executable, "-B", str(ENTRYPOINT)]
        return subprocess.run([*command, *map(str, args)], env=self.env if env is None else env,
                              capture_output=True, text=True, timeout=timeout)

    def initialize(self, project, *, article_type=None, language="bilingual", force=False,
                   template="angew"):
        with contextlib.redirect_stdout(io.StringIO()):
            templates.initialize(project, force, template, language=language, article_type=article_type)

    def assert_success(self, result, context=""):
        self.assertEqual(result.returncode, 0, context + "\n" + result.stdout + result.stderr)

    def inventory(self, root):
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}

    def assert_clean(self, project):
        self.assertEqual([str(path.relative_to(project)) for path in project.rglob("*")
                          if path.is_file() and path.suffix.lower() in INTERMEDIATES], [])


class AngewTests(AngewSupport, unittest.TestCase):
    def test_four_types_initialize_offline_in_both_languages_and_chinese_paths(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("unexpected download")) as fetch:
            for language in ("bilingual", "english"):
                for kind in ARTICLE_TYPES:
                    with self.subTest(language=language, article_type=kind):
                        project = self.root / "中文 manuscript paths" / language / kind
                        self.initialize(project, article_type=kind, language=language)
                        metadata = json.loads((project / templates.METADATA_NAME).read_text())
                        self.assertEqual(metadata["schema_version"], 1)
                        self.assertEqual(metadata["template"], "angew")
                        self.assertEqual(metadata["template_id"], "journal/angewandte-chemie-international-edition")
                        self.assertEqual(metadata["article_type"], kind)
                        self.assertEqual(metadata["language"], language)
                        self.assertEqual(metadata["engine"], "xelatex" if language == "bilingual" else "pdflatex")
                        self.assertEqual(templates.template_article_type_for_project(project), kind)
                        self.assertNotIn(str(self.root), json.dumps(metadata))
                        self.assertTrue((project / "prism-wiley-article.cls").is_file())
                        self.assertTrue((project / "prism-angew.bst").is_file())
                        self.assertTrue((project / "wiley-template-NOTICE.md").is_file())
                        self.assertTrue((project / "wiley-template-LICENSE.txt").is_file())
                        self.assertFalse(any((project / other).exists() for other in ARTICLE_TYPES))
                        self.assertFalse((project / "common").exists())
                        self.assertFalse(list(project.glob("*.zip")))
                        for name in ("main.tex", "supplementary.tex", "examples.tex"):
                            self.assertEqual("\\usepackage{prism-cjk}" in (project / name).read_text(),
                                             language == "bilingual", name)
                        source = templates.ASSET_DIR / "angew-template" / kind / "supplementary.tex"
                        if not source.is_file():
                            source = templates.ASSET_DIR / "angew-template/common/supplementary.tex"
                        if language == "english":
                            self.assertEqual((project / "supplementary.tex").read_bytes(), source.read_bytes())
                        self.assert_clean(project)
        fetch.assert_not_called()

    def test_default_canonical_id_and_legacy_metadata_remain_read_only(self):
        project = self.root / "default project"
        self.initialize(project, template="journal/angewandte-chemie-international-edition")
        self.assertEqual(templates.template_for_project(project), "angew")
        self.assertEqual(templates.template_article_type_for_project(project), "research")
        path = project / templates.METADATA_NAME
        metadata = json.loads(path.read_text())
        metadata.pop("article_type")
        original = (json.dumps(metadata) + "\n").encode()
        path.write_bytes(original)
        self.assertEqual(templates.template_article_type_for_project(project), "research")
        self.assertEqual(path.read_bytes(), original)
        for value in ("unknown", [], {}, True, 1, None):
            with self.subTest(value=value):
                invalid = dict(metadata, article_type=value)
                original = json.dumps(invalid).encode()
                path.write_bytes(original)
                with self.assertRaisesRegex(SystemExit, "Invalid Prism template metadata"):
                    templates.template_for_project(project)
                self.assertEqual(path.read_bytes(), original)

    def test_cross_journal_types_and_ordinary_build_options_preserve_user_material(self):
        target = self.root / "existing author folder"
        target.mkdir()
        (target / "local.txt").write_bytes(b"synthetic user material")
        before = self.inventory(target)
        for args in (("--init", target, "--force", "--template", "nar", "--article-type", "review"),
                     ("--init", target, "--force", "--template", "angew", "--article-type", "database"),
                     ("--init", target, "--force", "--template", "angew", "--article-type", "web-server"),
                     ("--init", target, "--force", "--template", "bib", "--article-type", "minireview"),
                     (target, "--article-type", "review"),
                     ("--list-templates", "--article-type", "review")):
            with self.subTest(args=args):
                failed = self.cli(*args)
                self.assertNotEqual(failed.returncode, 0)
                self.assertEqual(self.inventory(target), before)
                self.assertEqual(list(target.parent.glob(target.name + ".backup*")), [])

    def test_nar_types_survive_generic_article_asset_selection(self):
        for kind in ("research", "database", "web-server"):
            with self.subTest(kind=kind):
                target = self.root / "NAR" / kind
                self.initialize(target, template="nar", article_type=kind, language="english")
                self.assertEqual(templates.template_article_type_for_project(target), kind)
                self.assertTrue((target / "graphical_abstract.tex").is_file())
                self.assertTrue((target / "prism-nar.bst").is_file())
                self.assertFalse((target / "prism-wiley-article.cls").exists())
                self.assertEqual((target / "main.tex").read_bytes(),
                                 (templates.ASSET_DIR / "nar-template" / kind / "main.tex").read_bytes())

    def test_dependency_preview_is_read_only_and_language_specific(self):
        target = self.root / "preview review"
        self.initialize(target, article_type="review")
        before = self.inventory(target)
        no_tools = self.root / "no TeX"
        no_tools.mkdir()
        env = dict(self.env, PATH=str(no_tools))
        mixed = self.cli(target, "--check-deps", "--article-type", "minireview", env=env)
        self.assertNotEqual(mixed.returncode, 0)
        self.assertIn("xelatex: MISSING", mixed.stdout)
        self.assertIn("prism-wiley-article.cls", mixed.stdout)
        self.assertIn("prism-angew.bst", mixed.stdout)
        self.assertEqual(self.inventory(target), before)
        english = self.cli("--check-deps", "--template", "angew", "--language", "english",
                           "--article-type", "communication", env=env)
        self.assertNotEqual(english.returncode, 0)
        self.assertIn("pdflatex: MISSING", english.stdout)
        self.assertNotIn("Fandol", english.stdout)
        self.assertNotIn("xeCJK", english.stdout)

    def test_force_backup_preserves_the_entire_original_project(self):
        target = self.root / "original project"
        self.initialize(target, article_type="communication", language="english")
        (target / "local.txt").write_bytes(b"synthetic local note")
        before = self.inventory(target)
        with self.assertRaisesRegex(SystemExit, "not empty"):
            self.initialize(target, article_type="review")
        self.assertEqual(self.inventory(target), before)
        self.initialize(target, article_type="review", force=True)
        self.assertEqual(self.inventory(target.with_name(target.name + ".backup")), before)
        self.assertEqual(templates.template_article_type_for_project(target), "review")

    def test_corrupt_or_missing_resources_do_not_move_targets(self):
        assets = self.root / "copied assets"
        shutil.copytree(templates.ASSET_DIR, assets)
        original_class = assets / "upstream/wiley-overleaf/2019/wiley-article.cls"
        content = original_class.read_bytes()
        original_class.write_bytes(content[:-1] + (b"!" if content[-1:] != b"!" else b"?"))
        target = self.root / "preserved project"
        target.mkdir()
        (target / "local.txt").write_bytes(b"synthetic author content")
        before = self.inventory(target)
        missing_parent = self.root / "uncreated parent" / "paper"
        with mock.patch.object(templates, "ASSET_DIR", assets):
            for path, force in ((target, True), (missing_parent, False)):
                with self.subTest(path=path):
                    with self.assertRaisesRegex(SystemExit, "checksum mismatch"):
                        self.initialize(path, article_type="review", force=force)
                    self.assertEqual(self.inventory(target), before)
                    self.assertFalse(missing_parent.parent.exists())
                    self.assertEqual(list(target.parent.glob(target.name + ".backup*")), [])
            original_class.write_bytes(content)
            (assets / "angew-template/common/prism-angew.bst").unlink()
            with self.assertRaisesRegex(SystemExit, "missing"):
                self.initialize(target, article_type="review", force=True)
            self.assertEqual(self.inventory(target), before)
            self.assertEqual(list(target.parent.glob(target.name + ".backup*")), [])


class AngewCompilationTests(AngewSupport, unittest.TestCase):
    def require_real_tex(self):
        for command in ("xelatex", "pdflatex", "latexmk", "bibtex", "kpsewhich", "pdftotext"):
            if not shutil.which(command):
                self.skipTest(f"Angew compilation tests require {command}")
        for resource in ("FandolSong-Regular.otf", "FandolHei-Regular.otf", "XITSMath-Regular.otf",
                         "mdframed.sty", "authblk.sty", "mhchem.sty"):
            result = subprocess.run(["kpsewhich", resource], capture_output=True, text=True)
            if result.returncode or not result.stdout.strip():
                self.skipTest(f"Angew compilation tests require {resource}")

    def text_of(self, pdf):
        return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True,
                              text=True, check=True, timeout=30).stdout

    def add_chinese(self, path):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"(\\title(?:\[[^\]]*\])?\{)", lambda match: match.group(1) + "中文标题 ", text, count=1)
        text = re.sub(r"(\\author(?:\[[^\]]*\])?\{)", lambda match: match.group(1) + "中文作者 ", text, count=1)
        snippet = (
            "\n中文正文 English text。\n"
            "\\begin{figure}[htbp]\\centering\\fbox{Example}"
            "\\caption{中文图注 Mixed caption}\\end{figure}\n"
            "\\begin{table}[htbp]\\centering\\caption{中文表格 Mixed table}"
            "\\begin{tabular}{ll}中文表头 & Value\\\\数据 & 1\\end{tabular}\\end{table}\n"
            "\\[x=\\text{中文公式}\\]\n"
        )
        marker = r"\bibliographystyle"
        position = text.find(marker)
        if position < 0:
            position = text.index(r"\end{document}")
        path.write_text(text[:position] + snippet + text[position:], encoding="utf-8")

    def test_four_types_and_supplements_compile_in_both_languages(self):
        self.require_real_tex()

        def check_project(language, kind):
            target = self.root / "编译 projects" / language / kind
            self.assert_success(self.cli("--init", target, "--template", "angew", "--article-type", kind,
                                         "--language", language))
            metadata = (target / templates.METADATA_NAME).read_bytes()
            if language == "bilingual":
                self.add_chinese(target / "main.tex")
            self.assert_success(self.cli(target, "--strict"), f"{language}/{kind}/main.tex")
            pdf = target / "main.pdf"
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))
            extracted = self.text_of(pdf)
            compact = re.sub(r"\s+", " ", extracted).casefold()
            # Wiley's letter-spaced headings can extract with spaces inside
            # words; compare their semantic text independently of PDF spacing.
            unspaced = re.sub(r"\s+", "", extracted).casefold()
            self.assertIn("wilkinson", compact)
            self.assertRegex(compact, r"scheme\s+1")
            if kind in ("review", "minireview"):
                self.assertIn("summaryandoutlook", unspaced)
                self.assertIn("first author", compact)
                self.assertIn("1|introduction", unspaced)
            # The TOC text and graphic are embedded on the last main page.
            last_page = extracted.rstrip("\f\n ").split("\f")[-1].casefold()
            self.assertTrue("tableofcontents" in re.sub(r"\s+", "", last_page) or "toc" in last_page,
                            f"No TOC entry on final page: {last_page}")
            if language == "bilingual":
                for expected in ("中文标题", "中文作者", "中文正文", "中文图注", "中文表格", "中文表头", "中文公式"):
                    self.assertIn(expected, extracted)
            script = (target / "prism-build.sh").read_bytes()
            self.assertEqual((target / templates.METADATA_NAME).read_bytes(), metadata)
            self.assert_clean(target)
            supplement = target / "supplementary.tex"
            if language == "bilingual":
                self.add_chinese(supplement)
            self.assert_success(self.cli(target, "--main", supplement.name, "--strict", "--no-build-script"),
                                f"{language}/{kind}/supplementary.tex")
            support_text = self.text_of(supplement.with_suffix(".pdf"))
            self.assertIn("contents", support_text.casefold())
            self.assertRegex(support_text.casefold(), r"table\s+s1")
            self.assertEqual((target / "prism-build.sh").read_bytes(), script)
            self.assert_clean(target)
            if kind == "research":
                examples = target / "examples.tex"
                if language == "bilingual":
                    self.add_chinese(examples)
                self.assert_success(self.cli(target, "--main", examples.name, "--strict", "--no-build-script"),
                                    f"{language}/examples.tex")
                self.assertEqual((target / "prism-build.sh").read_bytes(), script)
                self.assert_clean(target)
                # A failed late rebuild preserves the successfully published PDF.
                pdf_digest = hashlib.sha256(pdf.read_bytes()).digest()
                main = target / "main.tex"
                text = main.read_text()
                main.write_text(text.replace(r"\end{document}", "\\UndefinedPrismTestCommand\n" + r"\end{document}", 1))
                failure = self.cli(target, "--strict")
                self.assertNotEqual(failure.returncode, 0)
                self.assertEqual(hashlib.sha256(pdf.read_bytes()).digest(), pdf_digest)
                self.assertEqual((target / "prism-build.sh").read_bytes(), script)
                self.assert_clean(target)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(check_project, language, kind): (language, kind)
                       for language in ("bilingual", "english") for kind in ARTICLE_TYPES}
            for future in concurrent.futures.as_completed(futures):
                with self.subTest(language=futures[future][0], article_type=futures[future][1]):
                    future.result()


if __name__ == "__main__":
    unittest.main()
