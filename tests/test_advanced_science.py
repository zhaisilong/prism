"""Exercise Advanced Science profiles and the shared numeric Wiley bibliography."""

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
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from prism_latex import templates
from prism_test_support import TemplateSupport, require_tex

PAPER = ROOT / "scripts" / "latex-paper.sh"
ENTRYPOINT = ROOT / "skills/paper-latex/scripts/paper_latex.py"
ALIAS = "advanced-science"
CANONICAL = "journal/advanced-science"
ARTICLE_TYPES = ("research", "review", "perspective")
STYLE = "prism-wiley-numeric.bst"


class AdvancedScienceSupport(TemplateSupport):
    default_template = "advanced-science"


class AdvancedScienceTests(AdvancedScienceSupport, unittest.TestCase):
    def test_three_types_initialize_offline_in_both_languages_and_chinese_paths(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network")) as fetch:
            for language in ("bilingual", "english"):
                for kind in ARTICLE_TYPES:
                    with self.subTest(language=language, article_type=kind):
                        project = self.root / "中文 projects with spaces" / language / kind
                        self.initialize(project, article_type=kind, language=language,
                                        template=CANONICAL if language == "english" else ALIAS)
                        metadata = json.loads((project / templates.METADATA_NAME).read_text())
                        self.assertEqual(metadata["schema_version"], 1)
                        self.assertEqual(metadata["template"], ALIAS)
                        self.assertEqual(metadata["template_id"], CANONICAL)
                        self.assertEqual(metadata["article_type"], kind)
                        self.assertEqual(metadata["language"], language)
                        self.assertEqual(metadata["engine"], "xelatex" if language == "bilingual" else "pdflatex")
                        self.assertEqual(templates.template_article_type_for_project(project), kind)
                        self.assertNotIn(str(self.root), json.dumps(metadata))
                        self.assertTrue((project / STYLE).is_file())
                        self.assertTrue((project / "references.bib").is_file())
                        self.assertFalse(list(project.glob("*.zip")))
                        for unexpected in (*ARTICLE_TYPES, "common", "prism-angew.bst",
                                           "prism-wiley-article.cls", "wiley-article.cls"):
                            self.assertFalse((project / unexpected).exists(), unexpected)
                        for name in ("main.tex", "supplementary.tex", "examples.tex"):
                            self.assertEqual(r"\usepackage{prism-cjk}" in (project / name).read_text(),
                                             language == "bilingual", name)
                        if language == "english":
                            assets = templates.ASSET_DIR / "advanced-science-template"
                            self.assertEqual((project / "main.tex").read_bytes(),
                                             (assets / kind / "main.tex").read_bytes())
                            support = assets / kind / "supplementary.tex"
                            if not support.is_file():
                                support = assets / "common" / "supplementary.tex"
                            self.assertEqual((project / "supplementary.tex").read_bytes(), support.read_bytes())
                        self.assert_clean(project)
        fetch.assert_not_called()

    def test_default_and_legacy_metadata_are_read_only_and_invalid_types_fail(self):
        project = self.root / "default manuscript"
        self.initialize(project, template=CANONICAL)
        self.assertEqual(templates.template_for_project(project), ALIAS)
        self.assertEqual(templates.template_article_type_for_project(project), "research")
        path = project / templates.METADATA_NAME
        metadata = json.loads(path.read_text())
        metadata.pop("article_type")
        original = (json.dumps(metadata) + "\n").encode()
        path.write_bytes(original)
        self.assertEqual(templates.template_article_type_for_project(project), "research")
        self.assertEqual(path.read_bytes(), original)
        for value in ("communication", "unknown", [], {}, True, 1, None):
            with self.subTest(value=value):
                invalid = dict(metadata, article_type=value)
                original = json.dumps(invalid).encode()
                path.write_bytes(original)
                with self.assertRaisesRegex(SystemExit, "Invalid Prism template metadata"):
                    templates.template_for_project(project)
                self.assertEqual(path.read_bytes(), original)

    def test_catalog_and_dependency_preview_are_offline_and_use_light_article_profile(self):
        no_tex = dict(self.env, PATH="")
        result = self.cli("--list-templates", "--group-by", "publisher", env=no_tex)
        self.assert_success(result)
        wiley = result.stdout.split("\nWiley-VCH\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn("advanced-science: Advanced Science", wiley)
        self.assertIn("science-advances: Science Advances", result.stdout)
        block = re.search(r"(?m)^  advanced-science:.*(?:\n    .*?)*(?=\n  \S|\n\S|\Z)", result.stdout)
        self.assertIsNotNone(block, result.stdout)
        self.assertIn(CANONICAL, block.group())
        self.assertIn("default: research", block.group())
        for kind in ARTICLE_TYPES:
            self.assertIn(kind, block.group())
        project = self.root / "read only preview"
        self.initialize(project, article_type="review")
        before = self.inventory(project)
        mixed = self.cli(project, "--check-deps", "--article-type", "perspective", env=no_tex)
        self.assertNotEqual(mixed.returncode, 0)
        self.assertIn("xelatex: MISSING", mixed.stdout)
        self.assertIn(STYLE, mixed.stdout)
        self.assertIn("xeCJK.sty: MISSING", mixed.stdout)
        self.assertEqual(self.inventory(project), before)
        english = self.cli("--check-deps", "--template", CANONICAL, "--language", "english",
                           "--article-type", "research", env=no_tex)
        self.assertNotEqual(english.returncode, 0)
        self.assertIn("pdflatex: MISSING", english.stdout)
        self.assertIn("natbib.sty: MISSING", english.stdout)
        for text in ("xeCJK", "Fandol", "XITSMath", "Lato", "lato.sty", "prism-wiley-article", "prism-angew"):
            self.assertNotIn(text, english.stdout)

    def test_illegal_options_do_not_create_directories_or_backup_author_material(self):
        target = self.root / "existing author folder"
        target.mkdir()
        (target / "local.txt").write_bytes(b"synthetic author material")
        before = self.inventory(target)
        for options in (
            ("--init", target, "--force", "--template", ALIAS, "--article-type", "communication"),
            ("--init", target, "--force", "--template", ALIAS, "--article-type", "database"),
            ("--init", target, "--force", "--template", ALIAS, "--language", "unknown"),
            ("--init", target, "--force", "--template", ALIAS, "--template-source", self.root / "unused.zip"),
            ("--init", target, "--force", "--template", "angew", "--article-type", "perspective"),
            ("--init", target, "--force", "--template", "science-advances", "--article-type", "research"),
            (target, "--article-type", "review"),
            ("--list-templates", "--article-type", "perspective"),
        ):
            with self.subTest(options=options):
                failed = self.cli(*options)
                self.assertNotEqual(failed.returncode, 0)
                self.assertEqual(self.inventory(target), before)
                self.assertFalse(list(target.parent.glob(target.name + ".backup*")))
        missing = self.root / "uncreated parent" / "paper"
        result = self.cli("--init", missing, "--template", ALIAS, "--article-type", "database")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(missing.parent.exists())

    def test_force_creates_exact_backup_and_only_selected_type_replaces_it(self):
        target = self.root / "中文 original paper"
        self.initialize(target, article_type="research", language="english")
        (target / "local.txt").write_bytes(b"synthetic local notes")
        before = self.inventory(target)
        with self.assertRaisesRegex(SystemExit, "not empty"):
            self.initialize(target, article_type="review")
        self.assertEqual(self.inventory(target), before)
        self.initialize(target, article_type="review", force=True)
        self.assertEqual(self.inventory(target.with_name(target.name + ".backup")), before)
        self.assertEqual(templates.template_article_type_for_project(target), "review")
        self.assertFalse((target / "local.txt").exists())

    def test_missing_selected_or_shared_assets_fail_before_targets_are_moved(self):
        assets = self.root / "copied public assets"
        shutil.copytree(templates.ASSET_DIR, assets)
        target = self.root / "preserved target"
        target.mkdir()
        (target / "local.txt").write_bytes(b"synthetic author content")
        before = self.inventory(target)
        missing_parent = self.root / "uncreated resource target" / "paper"
        for relative in (
            Path(STYLE),
            Path("advanced-science-template/common/supplementary.tex"),
            Path("advanced-science-template/common/references.bib"),
            Path("advanced-science-template/common/NOTICE.md"),
            Path("advanced-science-template/review/main.tex"),
        ):
            with self.subTest(resource=relative):
                path = assets / relative
                content = path.read_bytes()
                path.unlink()
                try:
                    with mock.patch.object(templates, "ASSET_DIR", assets):
                        for destination, force in ((target, True), (missing_parent, False)):
                            with self.assertRaisesRegex(SystemExit, "missing"):
                                self.initialize(destination, article_type="review", force=force)
                    self.assertEqual(self.inventory(target), before)
                    self.assertFalse(list(target.parent.glob(target.name + ".backup*")))
                    self.assertFalse(missing_parent.parent.exists())
                finally:
                    path.write_bytes(content)


class AdvancedScienceCompilationTests(AdvancedScienceSupport, unittest.TestCase):
    def require_real_tex(self):
        require_tex(self, ('natbib.sty', 'newfloat.sty', 'mhchem.sty', 'FandolSong-Regular.otf', 'FandolHei-Regular.otf'))

    def add_chinese(self, path):
        text = path.read_text()
        text = re.sub(r"(\\title\{)", lambda match: match.group(1) + "中文标题 ", text, count=1)
        text = re.sub(r"(\\author\{)", lambda match: match.group(1) + "中文作者 ", text, count=1)
        text = re.sub(r"(\\caption\{)", lambda match: match.group(1) + "中文图表 ", text, count=1)
        path.write_text(text)

    def test_three_types_main_and_supplement_compile_in_both_languages(self):
        self.require_real_tex()

        def check_project(language, kind):
            target = self.root / "编译 projects with spaces" / language / kind
            self.initialize(target, article_type=kind, language=language)
            metadata = (target / templates.METADATA_NAME).read_bytes()
            if language == "bilingual":
                self.add_chinese(target / "main.tex")
            self.assert_success(self.cli(target, "--strict"), f"{language}/{kind}/main")
            extracted = self.text_of(target / "main.pdf")
            self.assertIn("Wilkinson", extracted)
            self.assertIn("Scheme 1", extracted)
            last_page = extracted.rstrip("\f\n ").split("\f")[-1]
            self.assertIn("Table of Contents", last_page)
            if kind == "research":
                self.assertIn("Statistical Analysis", extracted)
            else:
                self.assertIn("First Author", extracted)
                self.assertIn("biograph", extracted.lower())
            if language == "bilingual":
                for marker in ("中文标题", "中文作者", "中文图表"):
                    self.assertIn(marker, extracted)
            script = (target / "prism-build.sh").read_bytes()
            self.assert_clean(target)
            supplement = target / "supplementary.tex"
            if language == "bilingual":
                self.add_chinese(supplement)
            self.assert_success(self.cli(target, "--main", supplement.name, "--strict", "--no-build-script"),
                                f"{language}/{kind}/supplement")
            support = self.text_of(supplement.with_suffix(".pdf"))
            first_page = support.split("\f")[0]
            self.assertIn("Contents", first_page)
            self.assertRegex(first_page, r"(?m)^\s*S1\s*$")
            for expected in ("Figure S1", "Table S1", "Scheme S1"):
                self.assertIn(expected, support)
            self.assertRegex(support, r"\(S1\)")
            self.assertEqual((target / "prism-build.sh").read_bytes(), script)
            self.assertEqual((target / templates.METADATA_NAME).read_bytes(), metadata)
            self.assert_clean(target)
            if language == "bilingual":
                for marker in ("中文标题", "中文作者", "中文图表"):
                    self.assertIn(marker, support)
            if kind == "research":
                examples = target / "examples.tex"
                if language == "bilingual":
                    self.add_chinese(examples)
                self.assert_success(self.cli(target, "--main", examples.name, "--strict", "--no-build-script"),
                                    f"{language}/examples")
                self.assertEqual((target / "prism-build.sh").read_bytes(), script)
                self.assert_clean(target)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(check_project, language, kind): (language, kind)
                       for language in ("bilingual", "english") for kind in ARTICLE_TYPES}
            for future in concurrent.futures.as_completed(futures):
                with self.subTest(language=futures[future][0], article_type=futures[future][1]):
                    future.result()

    def test_actual_numeric_style_author_boundary_order_links_and_pdf_failure_preservation(self):
        self.require_real_tex()
        if not shutil.which("pdftohtml"):
            self.skipTest("Advanced Science DOI link test requires pdftohtml")
        project = self.root / "numeric bibliography fixture"
        self.initialize(project, language="english")
        main = (project / "main.tex").read_text()
        preamble = main.split(r"\begin{document}", 1)[0]
        style = re.search(r"\\bibliographystyle\{([^}]+)\}", main)
        self.assertIsNotNone(style, main)
        self.assertEqual(style.group(1), "prism-wiley-numeric")
        fixture = project / "citation-check.tex"
        document = (preamble + "\n" + r"\begin{document}" + "\n"
                    + r"FirstMarker \cite{zulu}; SecondMarker \cite{alpha}." + "\n"
                    + style.group() + "\n" + r"\bibliography{fixture}" + "\n"
                    + r"\end{document}" + "\n")
        fixture.write_text(document)
        six_names = ("Sixone", "Sixtwo", "Sixthree", "Sixfour", "Sixfive", "Sixlast")
        seven_names = ("Sevenone", "Seventwo", "Seventhree", "Sevenfour", "Sevenfive", "Sevensix", "Sevenlast")
        records = []
        for key, names, title, tail in (
            ("alpha", six_names, "Complete Six Author Title", "volume={8}, number={2}, eid={e202600001}"),
            ("zulu", seven_names, "Complete Seven Author Title", "volume={7}, number={3}, pages={11--19}"),
        ):
            doi = ("https://doi.org/" if key == "alpha" else "") + "10.0000/prism-wiley-" + key
            records.append("@article{" + key + ",\n author={"
                           + " and ".join(name + ", Alice" for name in names)
                           + "},\n title={" + title + "},\n journal={Full Synthetic Journal Name},"
                           + " year={2026}, " + tail + ", doi={" + doi + "}\n}\n")
        bibliography = "\n".join(records)
        (project / "fixture.bib").write_text(bibliography)
        before = self.inventory(project)
        arguments = (project, "--main", fixture.name, "--strict", "--no-build-script")
        self.assert_success(self.cli(*arguments))
        pdf = fixture.with_suffix(".pdf")
        raw = " ".join(self.text_of(pdf, "-raw").split())
        self.assertRegex(raw, r"FirstMarker\s*\[1\];\s*SecondMarker\s*\[2\]\.")
        self.assertLess(raw.index("Complete Seven Author Title"), raw.index("Complete Six Author Title"))
        first = raw.split("Complete Seven Author Title", 1)[0]
        for author in seven_names[:3]:
            self.assertIn(author, first)
        for author in seven_names[3:]:
            self.assertNotIn(author, first)
        self.assertIn("et al.", first)
        second = raw.split("Complete Seven Author Title", 1)[1]
        for author in six_names:
            self.assertIn(author, second)
        self.assertNotIn("et al.", second)
        self.assertIn("Full Synthetic Journal Name", raw)
        self.assertIn("e202600001", raw)
        self.assertRegex(raw, r"7\(3\):11\s*[-\u2013]\s*19")
        self.assertIn("8(2):e202600001", raw)
        words = list(ET.fromstring(self.text_of(pdf, "-bbox")).iter("{http://www.w3.org/1999/xhtml}word"))
        for marker, citation in (("FirstMarker", "[1];"), ("SecondMarker", "[2].")):
            index = next(i for i, word in enumerate(words) if word.text == marker)
            number = next(word for word in words[index + 1:index + 4] if word.text == citation)
            self.assertLess(abs(float(number.attrib["yMax"]) - float(words[index].attrib["yMax"])), 1.0)
        html = subprocess.run(["pdftohtml", "-stdout", "-i", "-noframes", str(pdf)],
                              capture_output=True, text=True, check=True, timeout=30).stdout
        for key in ("alpha", "zulu"):
            self.assertIn('href="https://doi.org/10.0000/prism-wiley-' + key + '"', html)
        self.assertNotIn("doi.org/https", html)
        for relative, content in before.items():
            self.assertEqual((project / relative).read_bytes(), content)
        self.assert_clean(project)
        previous_pdf = pdf.read_bytes()
        fixture.write_text(document.replace(r"\end{document}", r"\UndefinedAdvancedScienceFixture" + "\n"
                                            + r"\end{document}", 1))
        failed = self.cli(*arguments)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(pdf.read_bytes(), previous_pdf)
        self.assert_clean(project)


if __name__ == "__main__":
    unittest.main()
