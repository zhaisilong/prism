from __future__ import annotations

import concurrent.futures
import contextlib
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
from prism_test_support import TemplateSupport, require_tex

PAPER = ROOT / "scripts" / "latex-paper.sh"
ENTRYPOINT = ROOT / "skills" / "paper-latex" / "scripts" / "paper_latex.py"
ARTICLE_TYPES = ("research", "database", "web-server")


class NARTestSupport(TemplateSupport):
    default_template = "nar"


class NARTests(NARTestSupport, unittest.TestCase):
    def test_three_types_initialize_offline_in_both_languages_and_chinese_paths(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("unexpected download")) as fetch:
            for language in ("bilingual", "english"):
                for article_type in ARTICLE_TYPES:
                    with self.subTest(language=language, article_type=article_type):
                        project = self.root / "中文路径 with spaces" / language / article_type
                        self.initialize(project, language=language, article_type=article_type)
                        metadata = json.loads((project / templates.METADATA_NAME).read_text())
                        self.assertEqual(metadata["schema_version"], 1)
                        self.assertEqual(metadata["template"], "nar")
                        self.assertEqual(metadata["template_id"], "journal/nucleic-acids-research")
                        self.assertEqual(metadata["article_type"], article_type)
                        self.assertEqual(metadata["language"], language)
                        self.assertEqual(metadata["engine"], "xelatex" if language == "bilingual" else "pdflatex")
                        self.assertNotIn(str(self.root), json.dumps(metadata))
                        self.assertEqual(templates.template_article_type_for_project(project), article_type)
                        self.assertEqual({p.name for p in project.glob("*.tex")},
                                         {"main.tex", "supplementary.tex", "graphical_abstract.tex", "examples.tex"})
                        self.assertTrue((project / "prism-nar.bst").is_file())
                        self.assertFalse(any((project / kind).exists() for kind in ARTICLE_TYPES))
                        self.assertFalse((project / "common").exists())
                        self.assertFalse(list(project.glob("*.zip")))
                        for name in ("main.tex", "supplementary.tex", "graphical_abstract.tex", "examples.tex"):
                            self.assertEqual("\\usepackage{prism-cjk}" in (project / name).read_text(),
                                             language == "bilingual", name)
                        if language == "english":
                            source = templates.ASSET_DIR / "nar-template" / article_type / "main.tex"
                            self.assertEqual((project / "main.tex").read_bytes(), source.read_bytes())
                        self.assert_clean(project)
        fetch.assert_not_called()

    def test_default_and_canonical_id_resolve_to_research_and_are_discoverable(self):
        listing = self.cli("--list-templates")
        self.assert_success(listing)
        nar = next(line for line in listing.stdout.splitlines() if line.startswith("nar:"))
        self.assertIn("journal/nucleic-acids-research", nar)
        for kind in ARTICLE_TYPES:
            self.assertIn(kind, nar)
        project = self.root / "默认 NAR"
        self.assert_success(self.cli("--init", project, "--template", "journal/nucleic-acids-research"))
        self.assertEqual(templates.template_article_type_for_project(project), "research")
        self.assertEqual(templates.template_for_project(project), "nar")

    def test_invalid_types_and_conflicting_cli_options_preserve_existing_target(self):
        project = self.root / "existing project"
        project.mkdir()
        (project / "private.txt").write_text("synthetic local content", encoding="utf-8")
        before = self.inventory(project)
        for kind in ("unknown", "", [], True, 1):
            with self.subTest(article_type=kind):
                with self.assertRaises(SystemExit):
                    self.initialize(project, force=True, article_type=kind)
                self.assertEqual(self.inventory(project), before)
                self.assertEqual(list(project.parent.glob(project.name + ".backup*")), [])
        for arguments in (
            ("--init", project, "--force", "--template", "nar", "--article-type", "unknown"),
            ("--init", project, "--force", "--template", "bib", "--article-type", "research"),
            (project, "--article-type", "database"),
            ("--check-deps", "--template", "bib", "--article-type", "research"),
            ("--list-templates", "--article-type", "research"),
        ):
            with self.subTest(arguments=arguments):
                result = self.cli(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.inventory(project), before)
                self.assertEqual(list(project.parent.glob(project.name + ".backup*")), [])

    def test_dependency_preview_does_not_switch_project_or_require_a_compiler(self):
        project = self.root / "只读预览 NAR"
        self.initialize(project, article_type="database")
        before = self.inventory(project)
        empty_path = self.root / "no tools"
        empty_path.mkdir()
        env = self.env.copy()
        env["PATH"] = str(empty_path)
        for kind in ARTICLE_TYPES:
            with self.subTest(article_type=kind):
                preview = self.cli(project, "--check-deps", "--article-type", kind, env=env)
                self.assertNotEqual(preview.returncode, 0)
                self.assertIn("xelatex: MISSING", preview.stdout)
                self.assertIn("prism-nar.bst", preview.stdout)
                self.assertNotIn("Unsupported article type", preview.stderr)
                self.assertEqual(self.inventory(project), before)
        english = self.cli("--check-deps", "--template", "nar", "--language", "english",
                           "--article-type", "web-server", env=env)
        self.assertIn("pdflatex: MISSING", english.stdout)
        self.assertNotIn("xeCJK", english.stdout)

    def test_metadata_defaults_and_invalid_types_are_read_only(self):
        project = self.root / "metadata"
        project.mkdir()
        path = project / templates.METADATA_NAME
        for metadata, expected in (({"template": "nar"}, "research"),
                                   ({"schema_version": 1, "template": "nar",
                                     "template_id": "journal/nucleic-acids-research"}, "research"),
                                   ({"template": "bib"}, "manuscript")):
            original = (json.dumps(metadata) + "\n").encode()
            path.write_bytes(original)
            self.assertEqual(templates.template_article_type_for_project(project), expected)
            self.assertEqual(path.read_bytes(), original)
        for article_type in ("unknown", [], {}, True, 1, None):
            with self.subTest(article_type=article_type):
                original = json.dumps({"template": "nar", "article_type": article_type}).encode()
                path.write_bytes(original)
                with self.assertRaisesRegex(SystemExit, "Invalid Prism template metadata"):
                    templates.template_article_type_for_project(project)
                self.assertEqual(path.read_bytes(), original)

    def test_nonempty_target_is_protected_and_force_backs_up_the_original(self):
        project = self.root / "existing NAR"
        self.initialize(project, article_type="research", language="english")
        (project / "local.txt").write_bytes(b"synthetic author material")
        before = self.inventory(project)
        with self.assertRaisesRegex(SystemExit, "not empty"):
            self.initialize(project, article_type="database")
        self.assertEqual(self.inventory(project), before)
        self.initialize(project, article_type="database", force=True)
        backup = project.with_name(project.name + ".backup")
        self.assertEqual(self.inventory(backup), before)
        self.assertEqual(templates.template_article_type_for_project(project), "database")
        self.assertFalse((project / "local.txt").exists())

    def test_corrupt_upstream_is_rejected_before_force_backup_or_parent_creation(self):
        assets = self.root / "copied assets"
        assets.mkdir()
        for name in ("nar-template", "upstream"):
            shutil.copytree(templates.ASSET_DIR / name, assets / name)
        (assets / "paper-template").mkdir()
        shutil.copy2(templates.ASSET_DIR / "paper-template/examples.tex", assets / "paper-template/examples.tex")
        shutil.copy2(templates.ASSET_DIR / "prism-cjk.sty", assets / "prism-cjk.sty")
        damaged = assets / "upstream/oup/1.5/oup-authoring-template.cls"
        original = damaged.read_bytes()
        damaged.write_bytes(original[:-1] + (b"!" if original[-1:] != b"!" else b"?"))
        project = self.root / "keep original"
        project.mkdir()
        (project / "private.txt").write_bytes(b"synthetic local material")
        before = self.inventory(project)
        with mock.patch.object(templates, "ASSET_DIR", assets):
            with self.assertRaisesRegex(SystemExit, "checksum mismatch"):
                self.initialize(project, force=True, article_type="web-server")
            self.assertEqual(self.inventory(project), before)
            self.assertEqual(list(project.parent.glob(project.name + ".backup*")), [])
            missing_parent = self.root / "must not create" / "new project"
            with self.assertRaisesRegex(SystemExit, "checksum mismatch"):
                self.initialize(missing_parent, article_type="research")
            self.assertFalse(missing_parent.parent.exists())


class NARCompilationTests(NARTestSupport, unittest.TestCase):
    # Keep expensive coverage in a separate class, while sharing helpers.
    def require_real_tex(self):
        require_tex(self, ('xeCJK.sty', 'FandolSong-Regular.otf', 'FandolHei-Regular.otf'))

    def insert_bilingual_body(self, path):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"(\\title(?:\[[^\]]*\])?\{)", lambda match: match.group(1) + "中文标题 ", text, count=1)
        text = text.replace("First Author", "中文作者 First Author", 1)
        snippet = (
            "\n\\section{中文章节 Mixed}\n中文正文 English text。\n"
            "\\begin{figure}[htbp]\\centering\\fbox{Example}"
            "\\caption{中文图注 Mixed caption}\\end{figure}\n"
            "\\begin{table}[htbp]\\centering\\caption{中文表格 Mixed table}"
            "\\begin{tabular}{ll}中文表头 & Value\\\\数据 & 1\\end{tabular}\\end{table}\n"
            "\\[x=\\text{中文公式}\\]\n"
        )
        path.write_text(text.replace(r"\end{document}", snippet + r"\end{document}", 1), encoding="utf-8")

    def test_three_main_types_and_shared_documents_compile_without_source_artifacts(self):
        self.require_real_tex()

        def compile_project(language, article_type):
            project = self.root / "实际编译 with spaces" / language / article_type
            self.assert_success(self.cli("--init", project, "--template", "nar", "--language", language,
                                         "--article-type", article_type))
            metadata = (project / templates.METADATA_NAME).read_bytes()
            if language == "bilingual":
                self.insert_bilingual_body(project / "main.tex")
            result = self.cli(project, "--strict")
            self.assert_success(result)
            main_pdf = project / "main.pdf"
            self.assertTrue(main_pdf.read_bytes().startswith(b"%PDF"))
            extracted = self.text_of(main_pdf)
            self.assertIn("Wilkinson", extracted)
            if language == "bilingual":
                for expected in ("中文标题", "中文作者", "中文正文", "中文图注", "中文表格", "中文表头", "中文公式"):
                    self.assertIn(expected, extracted)
            script = (project / "prism-build.sh").read_bytes()
            self.assertEqual((project / templates.METADATA_NAME).read_bytes(), metadata)
            self.assert_clean(project)

            # All three types use identical supplements and example resources;
            # exercise each shared document once per language.
            if article_type == "research":
                for name in ("supplementary.tex", "graphical_abstract.tex", "examples.tex"):
                    path = project / name
                    if language == "bilingual" and name != "graphical_abstract.tex":
                        self.insert_bilingual_body(path)
                    elif language == "bilingual":
                        text = path.read_text(encoding="utf-8")
                        self.assertIn("Input", text)
                        path.write_text(text.replace("Input", "输入 Input", 1), encoding="utf-8")
                    result = self.cli(project, "--main", name, "--strict", "--no-build-script")
                    self.assertEqual(result.returncode, 0,
                                     f"{language}/{article_type}/{name}:\n{result.stdout}{result.stderr}")
                    self.assertTrue(path.with_suffix(".pdf").read_bytes().startswith(b"%PDF"))
                    if name == "graphical_abstract.tex":
                        text = self.text_of(path.with_suffix(".pdf"))
                        self.assertEqual(text.count("\f"), 1, "The graphical abstract must remain one page")
                        if language == "bilingual":
                            self.assertIn("输入", text)
                    self.assertEqual((project / "prism-build.sh").read_bytes(), script)
                    self.assert_clean(project)
                # A late compilation failure must not replace the good PDF or
                # the main document's rebuild entrypoint.
                original_pdf = main_pdf.read_bytes()
                main = project / "main.tex"
                source = main.read_text(encoding="utf-8")
                main.write_text(source.replace(r"\end{document}", r"\UndefinedPrismTestCommand" + "\n" + r"\end{document}", 1))
                failed = self.cli(project, "--strict")
                self.assertNotEqual(failed.returncode, 0)
                self.assertEqual(main_pdf.read_bytes(), original_pdf)
                self.assertEqual((project / "prism-build.sh").read_bytes(), script)
                self.assert_clean(project)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(compile_project, language, kind): (language, kind)
                       for language in ("bilingual", "english") for kind in ARTICLE_TYPES}
            for future in concurrent.futures.as_completed(futures):
                with self.subTest(language=futures[future][0], article_type=futures[future][1]):
                    future.result()


if __name__ == "__main__":
    unittest.main()
