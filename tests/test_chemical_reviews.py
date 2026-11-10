"""Exercise the Chemical Reviews draft through initialization and real ACS builds."""

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
CANONICAL = "journal/chemical-reviews"


class ChemicalReviewsSupport(TemplateSupport):
    default_template = "chemrev"


class ChemicalReviewsTests(ChemicalReviewsSupport, unittest.TestCase):
    def test_alias_and_canonical_initialize_offline_in_both_languages(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network")) as fetch:
            for language, alias in (("bilingual", "chemrev"), ("english", CANONICAL)):
                with self.subTest(language=language, alias=alias):
                    project = self.root / "中文目录 with spaces" / language
                    self.initialize(project, language=language, alias=alias)
                    metadata = json.loads((project / templates.METADATA_NAME).read_text())
                    self.assertEqual(metadata["schema_version"], 1)
                    self.assertEqual(metadata["template"], "chemrev")
                    self.assertEqual(metadata["template_id"], CANONICAL)
                    self.assertEqual(metadata["language"], language)
                    self.assertEqual(metadata["engine"], "xelatex" if language == "bilingual" else "pdflatex")
                    self.assertNotIn("article_type", metadata)
                    self.assertNotIn(str(self.root), json.dumps(metadata))
                    self.assertEqual(templates.template_article_type_for_project(project), "review")
                    self.assertEqual({path.name for path in project.glob("*.tex")},
                                     {"main.tex", "supplementary.tex", "examples.tex"})
                    self.assertTrue((project / "references.bib").is_file())
                    self.assertFalse(list(project.glob("*.zip")))
                    for name in ("main.tex", "supplementary.tex", "examples.tex"):
                        self.assertEqual("\\usepackage{prism-cjk}" in (project / name).read_text(),
                                         language == "bilingual", name)
                    if language == "english":
                        self.assertEqual((project / "main.tex").read_bytes(),
                                         (templates.ASSET_DIR / "chemical-reviews-template/main.tex").read_bytes())
                    self.assert_clean(project)
        fetch.assert_not_called()

    def test_catalog_and_dependency_preview_work_without_a_tex_installation(self):
        env = dict(self.env, PATH="")
        listed = self.cli("--list-templates", "--group-by", "publisher", env=env)
        self.assert_success(listed)
        block = re.search(r"(?m)^  chemrev:.*(?:\n    .*?)*(?=\n  \S|\n\S|\Z)", listed.stdout)
        self.assertIsNotNone(block, listed.stdout)
        self.assertIn("Chemical Reviews", block.group())
        self.assertIn(CANONICAL, block.group())
        self.assertNotIn("--article-type", block.group())
        acs = listed.stdout.split("\nACS\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn("chemrev:", acs)
        for language in ("bilingual", "english"):
            preview = self.cli("--check-deps", "--template", CANONICAL, "--language", language, env=env)
            self.assertNotEqual(preview.returncode, 0)
            self.assertIn(("xelatex" if language == "bilingual" else "pdflatex") + ": MISSING", preview.stdout)
            self.assertIn("achemso.sty: MISSING", preview.stdout)
            self.assertEqual("xeCJK.sty" in preview.stdout, language == "bilingual")

    def test_unsupported_options_are_rejected_before_backup_or_directory_changes(self):
        project = self.root / "existing draft"
        project.mkdir()
        (project / "author.txt").write_bytes(b"synthetic author material")
        before = self.inventory(project)
        for options in (
            ("--article-type", "review"),
            ("--article-type", "focus-review"),
            ("--template-source", self.root / "not-needed.zip"),
            ("--language", "unsupported"),
        ):
            with self.subTest(options=options):
                result = self.cli("--init", project, "--force", "--template", "chemrev", *options)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.inventory(project), before)
                self.assertFalse(list(project.parent.glob(project.name + ".backup*")))
        target = self.root / "must not create" / "draft"
        rejected = self.cli("--init", target, "--template", "chemrev", "--article-type", "review")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertFalse(target.parent.exists())

    def test_nonempty_project_is_preserved_and_explicit_force_creates_an_exact_backup(self):
        project = self.root / "综述稿 with spaces"
        self.initialize(project, language="english")
        (project / "author.txt").write_bytes(b"synthetic author material")
        before = self.inventory(project)
        with self.assertRaisesRegex(SystemExit, "not empty"):
            self.initialize(project)
        self.assertEqual(self.inventory(project), before)
        self.initialize(project, force=True)
        self.assertEqual(self.inventory(project.with_name(project.name + ".backup")), before)
        self.assertFalse((project / "author.txt").exists())
        self.assertEqual(templates.template_language_for_project(project), "bilingual")


class ChemicalReviewsCompilationTests(ChemicalReviewsSupport, unittest.TestCase):
    def require_real_tex(self, *, bilingual=False):
        commands = ["pdflatex", "latexmk", "bibtex", "kpsewhich", "pdftotext"]
        resources = ["achemso.sty", "achemso.bst", "natmove.sty"]
        if bilingual:
            commands.append("xelatex")
            resources.extend(("xeCJK.sty", "FandolSong-Regular.otf", "FandolHei-Regular.otf"))
        require_tex(self, resources, commands)

    def add_chinese(self, path):
        source = path.read_text()
        source = re.sub(r"(\\title\{)", lambda match: match.group(1) + "中文标题 ", source, count=1)
        source = source.replace("First Author", "中文作者 First Author", 1)
        source = re.sub(r"(\\caption\{)", lambda match: match.group(1) + "中文图表 ", source, count=1)
        path.write_text(source)

    def test_main_supplement_and_examples_compile_in_both_languages(self):
        self.require_real_tex(bilingual=True)

        def compile_language(language):
            project = self.root / "实际编译 with spaces" / language
            self.initialize(project, language=language)
            metadata = (project / templates.METADATA_NAME).read_bytes()
            if language == "bilingual":
                self.add_chinese(project / "main.tex")
            self.assert_success(self.cli(project, "--strict"))
            script = (project / "prism-build.sh").read_bytes()
            text = self.text_of(project / "main.pdf")
            self.assertIn("Contents", text)
            self.assertIn("Wilkinson", text)
            if language == "bilingual":
                self.assertIn("中文标题", text)
                self.assertIn("中文作者", text)
                self.assertIn("中文图表", text)
            for name in ("supplementary.tex", "examples.tex"):
                if language == "bilingual":
                    self.add_chinese(project / name)
                self.assert_success(self.cli(project, "--main", name, "--strict", "--no-build-script"))
                self.assertTrue((project / name).with_suffix(".pdf").read_bytes().startswith(b"%PDF"))
                self.assertEqual((project / "prism-build.sh").read_bytes(), script)
                extracted = self.text_of((project / name).with_suffix(".pdf"))
                if name == "supplementary.tex":
                    first_page = extracted.split("\f")[0]
                    self.assertIn("Contents", first_page)
                    self.assertRegex(first_page, r"(?m)^\s*S1\s*$")
                    self.assertIn("Figure S1", extracted)
                    self.assertIn("Table S1", extracted)
                if language == "bilingual":
                    self.assertIn("中文标题", extracted)
                    self.assertIn("中文图表", extracted)
            self.assertEqual((project / templates.METADATA_NAME).read_bytes(), metadata)
            self.assert_clean(project)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(compile_language, language): language for language in ("bilingual", "english")}
            for future in concurrent.futures.as_completed(futures):
                with self.subTest(language=futures[future]):
                    future.result()

    def test_real_bibliography_order_author_boundary_links_and_failure_preservation(self):
        self.require_real_tex()
        if not shutil.which("pdftohtml"):
            self.skipTest("Chemical Reviews DOI link test requires pdftohtml")
        project = self.root / "ACS bibliography"
        self.initialize(project, language="english")
        # Exercise the actual template preamble, not a separately specified
        # copy of its ACS settings. All fixture references below are synthetic.
        preamble = (project / "main.tex").read_text().split(r"\begin{document}", 1)[0]
        fixture = project / "citation-check.tex"
        document = (preamble + "\n" + r"\begin{document}" + "\n"
                    + r"FirstMarker\cite{zulu}; SecondMarker\cite{alpha}." + "\n"
                    + r"\bibliography{fixture}" + "\n" + r"\end{document}" + "\n")
        fixture.write_text(document)
        names_ten = ["Ten" + name for name in ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "last")]
        names_eleven = ["Eleven" + name for name in ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "omitted")]
        records = []
        for key, names, title in (("alpha", names_ten, "Complete Ten Author Title"),
                                   ("zulu", names_eleven, "Complete Eleven Author Title")):
            records.append("@article{" + key + ",\n author={" + " and ".join(name + ", Alice" for name in names)
                           + "},\n title={" + title + "},\n journal={Synth. J.}, year={2026}, volume={2}, pages={11--19},\n"
                           + " doi={10.0000/prism-chemrev-" + key + "}\n}\n")
        (project / "fixture.bib").write_text("\n".join(records))
        sentinel = project / "acs-citation-check.bib"
        sentinel.write_text("@Control{achemso-control,ctrl-article-title={no}}\n"
                            "@article{sentinel,author={Sentinel, Alice},title={Source-only sentinel},"
                            "journal={Synthetic Journal},year={2026}}\n")
        before = self.inventory(project)
        arguments = (project, "--main", fixture.name, "--strict", "--no-build-script")
        self.assert_success(self.cli(*arguments))
        pdf = fixture.with_suffix(".pdf")
        raw = self.text_of(pdf, "-raw")
        text = " ".join(raw.split())
        self.assertRegex(text, r"FirstMarker;\s*1\s*SecondMarker\.\s*2")
        self.assertLess(text.index("Complete Eleven Author Title"), text.index("Complete Ten Author Title"))
        first = text.split("(1)", 1)[1].split("(2)", 1)[0]
        second = text.split("(2)", 1)[1]
        for name in names_eleven[:10]:
            self.assertIn(name, first)
        self.assertNotIn(names_eleven[10], first)
        self.assertIn("et al.", first)
        for name in names_ten:
            self.assertIn(name, second)
        self.assertNotIn("et al.", second)
        self.assertIn("Synth. J.", first)
        self.assertRegex(first, r"11\s*[-\u2013]\s*19")

        boxes = ET.fromstring(self.text_of(pdf, "-bbox"))
        words = list(boxes.iter("{http://www.w3.org/1999/xhtml}word"))
        for marker, number in (("FirstMarker;", "1"), ("SecondMarker.", "2")):
            index = next(i for i, word in enumerate(words) if word.text == marker)
            citation = next(word for word in words[index + 1:index + 4] if word.text == number)
            self.assertLess(float(citation.attrib["yMax"]), float(words[index].attrib["yMax"]) - 1)
        html = subprocess.run(["pdftohtml", "-stdout", "-i", "-noframes", str(pdf)],
                              capture_output=True, text=True, check=True, timeout=30).stdout
        for key in ("alpha", "zulu"):
            self.assertIn('href="https://doi.org/10.0000/prism-chemrev-' + key + '"', html)
        for relative, content in before.items():
            self.assertEqual((project / relative).read_bytes(), content)
        self.assert_clean(project)

        previous = pdf.read_bytes()
        fixture.write_text(document.replace(r"\bibliography", r"Unresolved \cite{sentinel}." + "\n" + r"\bibliography", 1))
        failed = self.cli(*arguments)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("sentinel", failed.stdout + failed.stderr)
        self.assertEqual(pdf.read_bytes(), previous)
        self.assertEqual(sentinel.read_bytes(), before[sentinel.name])
        self.assert_clean(project)


if __name__ == "__main__":
    unittest.main()
