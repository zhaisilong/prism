"""Nature Methods starter contracts using synthetic temporary projects."""

from __future__ import annotations

import json
import re
import shutil
import sys
import unittest
from unittest import mock
import urllib.request

from prism_test_support import ROOT, TemplateSupport, require_tex

sys.path.insert(0, str(ROOT / "scripts/lib"))
from prism_latex import templates
from prism_latex.catalog import CATALOG


class NatureMethodsTests(TemplateSupport, unittest.TestCase):
    default_template = "nature-methods"
    canonical = "journal/nature-methods"
    kinds = ("article", "resource", "analysis")

    def test_catalog_group_alias_and_engine_preview_without_tex(self):
        detail = CATALOG.detail(self.canonical)
        self.assertEqual(detail["alias"], self.default_template)
        self.assertEqual(detail["publisher"], "Springer Nature")
        self.assertEqual(detail["article_types"], list(self.kinds))
        self.assertEqual(detail["default_article_type"], "article")
        self.assertTrue(detail["capabilities"]["article_type_selection"])
        self.assertFalse(detail["capabilities"]["official_package_import"])
        self.assertTrue(any(d["role"] == "extended_data" and d["standalone"] for d in detail["documents"]))
        env = dict(self.env, PATH="")
        listing = self.cli("--list-templates", "--group-by", "publisher", env=env)
        self.assert_success(listing)
        group = listing.stdout.split("\nSpringer Nature\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn("nature-methods:", group)
        self.assertIn(self.canonical, group)
        for language, engine in (("bilingual", "xelatex"), ("english", "pdflatex")):
            check = self.cli("--check-deps", "--template", self.canonical, "--language", language, env=env)
            self.assertNotEqual(check.returncode, 0)
            self.assertIn(engine + ": MISSING", check.stdout)

    def test_offline_initialization_metadata_and_structure(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network")) as fetch:
            for language in ("bilingual", "english"):
                for kind in self.kinds:
                    with self.subTest(language=language, kind=kind):
                        project = self.root / "中文 路径" / language / kind
                        self.initialize(project, template=self.canonical, article_type=kind, language=language)
                        meta = json.loads((project / templates.METADATA_NAME).read_text())
                        self.assertEqual((meta["schema_version"], meta["template"], meta["template_id"]),
                                         (1, self.default_template, self.canonical))
                        self.assertEqual((meta["article_type"], meta["language"], meta["engine"]),
                                         (kind, language, "xelatex" if language == "bilingual" else "pdflatex"))
                        self.assertEqual({p.name for p in project.glob("*.tex")},
                                         {"main.tex", "supplementary.tex", "extended_data.tex", "examples.tex"})
                        for name in ("main.tex", "supplementary.tex", "extended_data.tex", "examples.tex"):
                            self.assertEqual(r"\usepackage{prism-cjk}" in (project / name).read_text(),
                                             language == "bilingual", name)
                        main = (project / "main.tex").read_text()
                        self.assertNotRegex(main, r"\\section\*?\{Introduction\}")
                        self.assertIn(r"\section{Results}", main)
                        self.assertIn(r"\section{Discussion}", main)
                        discussion = main.split(r"\section{Discussion}", 1)[1].split(r"\section{Online Methods}", 1)[0]
                        self.assertNotIn(r"\subsection", discussion)
                        self.assertIn(r"\subsection", main.split(r"\section{Online Methods}", 1)[1])
                        self.assertNotIn(str(self.root), json.dumps(meta))
                        self.assert_clean(project)
            fetch.assert_not_called()
        target = self.root / "legacy"
        self.initialize(target)
        path = target / templates.METADATA_NAME
        metadata = json.loads(path.read_text())
        self.assertEqual(metadata.pop("article_type"), "article")
        original = (json.dumps(metadata) + "\n").encode()
        path.write_bytes(original)
        self.assertEqual(templates.template_article_type_for_project(target), "article")
        self.assertEqual(path.read_bytes(), original)

    def test_invalid_options_and_overwrite_backup(self):
        target = self.root / "已有稿件"
        self.initialize(target)
        (target / "author.txt").write_text("synthetic private content")
        before = self.inventory(target)
        for options in (("--article-type", "review"), ("--language", "invalid"),
                        ("--template-source", self.root / "not-opened.zip"), ("--engine", "lualatex")):
            with self.subTest(options=options):
                result = self.cli("--init", target, "--force", "--template", self.default_template, *options)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.inventory(target), before)
                self.assertFalse(target.with_name(target.name + ".backup").exists())
        self.initialize(target, article_type="analysis", force=True)
        self.assertEqual(self.inventory(target.with_name(target.name + ".backup")), before)
        self.assertEqual(templates.template_article_type_for_project(target), "analysis")

    def test_missing_resources_preserve_destination(self):
        assets = self.root / "assets"
        assets.mkdir()
        shutil.copytree(templates.ASSET_DIR / "nature-methods-template", assets / "nature-methods-template")
        (assets / "paper-template").mkdir()
        shutil.copy2(templates.ASSET_DIR / "paper-template/examples.tex", assets / "paper-template/examples.tex")
        shutil.copy2(templates.ASSET_DIR / "prism-cjk.sty", assets / "prism-cjk.sty")
        target = self.root / "existing"
        target.mkdir()
        (target / "keep.txt").write_text("synthetic content")
        before = self.inventory(target)
        for name in ("common/supplementary.tex", "common/extended_data.tex", "common/references.bib",
                     "common/NOTICE.md", "analysis/main.tex"):
            with self.subTest(resource=name):
                path = assets / "nature-methods-template" / name
                contents = path.read_bytes()
                path.unlink()
                try:
                    with mock.patch.object(templates, "ASSET_DIR", assets):
                        with self.assertRaisesRegex(SystemExit, "missing"):
                            self.initialize(target, article_type="analysis", force=True)
                    self.assertEqual(self.inventory(target), before)
                    self.assertFalse(target.with_name(target.name + ".backup").exists())
                finally:
                    path.write_bytes(contents)

    def test_real_builds_chinese_and_rebuild_entrypoint(self):
        require_tex(self, ("xeCJK.sty", "FandolSong-Regular.otf", "natbib.sty", "unsrt.bst"))
        for language in ("bilingual", "english"):
            for kind in self.kinds:
                with self.subTest(language=language, kind=kind):
                    project = self.root / "编译项目" / language / kind
                    self.initialize(project, article_type=kind, language=language)
                    if language == "bilingual":
                        for name in ("main.tex", "supplementary.tex", "extended_data.tex"):
                            path = project / name
                            text = path.read_text()
                            path.write_text(text.replace(r"\end{document}", "中文示例文字。\n" + r"\end{document}"))
                    self.assert_success(self.cli(project, "--strict", timeout=300))
                    if language == "bilingual":
                        self.assertIn("中文示例文字", self.text_of(project / "main.pdf"))
                    rebuild = project / "prism-build.sh"
                    previous = rebuild.read_bytes()
                    for name in ("supplementary.tex", "extended_data.tex"):
                        self.assert_success(self.cli(project, "--main", name, "--strict", "--no-build-script", timeout=300))
                        text = self.text_of(project / (name.removesuffix(".tex") + ".pdf"))
                        if name == "supplementary.tex":
                            self.assertRegex(text, r"Supplementary Figure\s+1")
                            self.assertRegex(text, r"Supplementary Table\s+1")
                            self.assertEqual(len(re.findall(r"(?im)^\s*(?:\d+\s+)?Supplementary references\s*$", text)), 1)
                            self.assertNotRegex(text, r"(?im)^\s*References\s*$")
                        else:
                            self.assertRegex(text, r"Extended Data Fig\.\s*1")
                            self.assertRegex(text, r"Extended Data Table\s+1")
                        if language == "bilingual":
                            self.assertIn("中文示例文字", text)
                    if kind == "article":
                        self.assert_success(self.cli(project, "--main", "examples.tex", "--strict", "--no-build-script", timeout=300))
                    self.assertEqual(rebuild.read_bytes(), previous)
                    self.assert_clean(project)

    def test_citation_order_and_failed_build_preserves_pdf(self):
        require_tex(self, ("natbib.sty", "unsrt.bst"))
        project = self.root / "citations"
        self.initialize(project, language="english")
        main = (project / "main.tex").read_text()
        preamble = main.split(r"\begin{document}", 1)[0]
        style = re.search(r"\\bibliographystyle\{[^}]+\}", main).group()
        document = (preamble + "\n" + r"\begin{document}" + "\n"
                    + r"FirstMarker \cite{zulu}; SecondMarker \cite{alpha}." + "\n"
                    + style + "\n" + r"\bibliography{fixture}" + "\n" + r"\end{document}" + "\n")
        fixture = project / "citation-check.tex"
        fixture.write_text(document)
        (project / "fixture.bib").write_text("\n".join(
            "@article{" + key + ", author={Example, Alice}, title={" + title
            + "}, journal={Synthetic Journal}, year={2026}, volume={2}, pages={11--19}}"
            for key, title in (("alpha", "Complete Alpha Article Title"), ("zulu", "Complete Zulu Article Title"))))
        args = (project, "--main", fixture.name, "--strict", "--no-build-script")
        self.assert_success(self.cli(*args))
        pdf = fixture.with_suffix(".pdf")
        text = " ".join(self.text_of(pdf, "-raw").split()).casefold()
        self.assertLess(text.index("complete zulu article title"), text.index("complete alpha article title"))
        previous = pdf.read_bytes()
        fixture.write_text(document.replace(r"\end{document}", r"\UndefinedSyntheticFixture" + "\n" + r"\end{document}"))
        self.assertNotEqual(self.cli(*args).returncode, 0)
        self.assertEqual(pdf.read_bytes(), previous)
        self.assert_clean(project)
