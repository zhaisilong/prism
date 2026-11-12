"""Dyes and Pigments starter contracts using synthetic temporary projects."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from unittest import mock
import urllib.request

from prism_test_support import ROOT, TemplateSupport, require_tex

sys.path.insert(0, str(ROOT / "scripts/lib"))
from prism_latex import templates
from prism_latex.catalog import CATALOG


class DyesTests(TemplateSupport, unittest.TestCase):
    default_template = "dyes"
    canonical = "journal/dyes-and-pigments"

    def test_catalog_alias_group_and_preview_without_tex(self):
        detail = CATALOG.detail("dyes")
        self.assertEqual(detail["id"], self.canonical)
        self.assertEqual(detail["publisher"], "Elsevier")
        self.assertEqual(detail["article_types"], ["research", "review"])
        self.assertEqual(detail["default_article_type"], "research")
        self.assertTrue(detail["capabilities"]["article_type_selection"])
        self.assertFalse(detail["capabilities"]["official_package_import"])
        self.assertNotIn("highlights.txt", {d["path"] for d in detail["documents"]})
        self.assertTrue(any(d["role"] == "graphical_abstract" and d["standalone"]
                            for d in detail["documents"]))
        env = dict(self.env, PATH="")
        listing = self.cli("--list-templates", "--group-by", "publisher", env=env)
        self.assert_success(listing)
        group = listing.stdout.split("\nElsevier\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn("dyes:", group)
        self.assertIn(self.canonical, group)
        for language, engine in (("bilingual", "xelatex"), ("english", "pdflatex")):
            check = self.cli("--check-deps", "--template", self.canonical,
                             "--language", language, env=env)
            self.assertNotEqual(check.returncode, 0)
            self.assertIn(engine + ": MISSING", check.stdout)
            self.assertIn("elsarticle.cls: MISSING", check.stdout)

    def test_all_profiles_initialize_offline_and_keep_metadata_compatible(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network")) as fetch:
            for language in ("bilingual", "english"):
                for kind in ("research", "review"):
                    with self.subTest(language=language, kind=kind):
                        project = self.root / "染料 manuscript" / language / kind
                        self.initialize(project, template=self.canonical if language == "english" else "dyes",
                                        article_type=kind, language=language)
                        meta = json.loads((project / templates.METADATA_NAME).read_text())
                        self.assertEqual(meta["schema_version"], 1)
                        self.assertEqual(meta["template"], "dyes")
                        self.assertEqual(meta["template_id"], self.canonical)
                        self.assertEqual(meta["article_type"], kind)
                        self.assertEqual(meta["language"], language)
                        self.assertEqual(meta["engine"], "xelatex" if language == "bilingual" else "pdflatex")
                        self.assertNotIn(str(self.root), json.dumps(meta))
                        self.assertEqual({p.name for p in project.glob("*.tex")},
                                         {"main.tex", "supplementary.tex", "examples.tex", "graphical_abstract.tex"})
                        self.assertTrue((project / "highlights.txt").is_file())
                        self.assertFalse(any((project / d).exists() for d in ("common", "research", "review")))
                        for name in ("main.tex", "supplementary.tex", "examples.tex", "graphical_abstract.tex"):
                            self.assertEqual(r"\usepackage{prism-cjk}" in (project / name).read_text(),
                                             language == "bilingual", name)
                        self.assert_clean(project)
            fetch.assert_not_called()
        project = self.root / "legacy"
        self.initialize(project)
        path = project / templates.METADATA_NAME
        metadata = json.loads(path.read_text())
        self.assertEqual(metadata.pop("article_type"), "research")
        original = (json.dumps(metadata) + "\n").encode()
        path.write_bytes(original)
        self.assertEqual(templates.template_article_type_for_project(project), "research")
        self.assertEqual(path.read_bytes(), original)

    def test_invalid_options_protect_existing_target_and_force_backs_up(self):
        project = self.root / "已有稿件"
        self.initialize(project)
        (project / "local.txt").write_text("synthetic author content")
        before = self.inventory(project)
        for options in (("--article-type", "perspective"), ("--language", "unknown"),
                        ("--template-source", self.root / "not-opened.zip"), ("--engine", "lualatex")):
            with self.subTest(options=options):
                result = self.cli("--init", project, "--force", "--template", "dyes", *options)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.inventory(project), before)
                self.assertFalse(project.with_name(project.name + ".backup").exists())
        result = self.cli("--init", project, "--template", "dyes", "--article-type", "review")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.inventory(project), before)
        self.initialize(project, article_type="review", force=True)
        self.assertEqual(self.inventory(project.with_name(project.name + ".backup")), before)
        self.assertEqual(templates.template_article_type_for_project(project), "review")

    def test_missing_resources_do_not_replace_target(self):
        assets = self.root / "assets"
        assets.mkdir()
        shutil.copytree(templates.ASSET_DIR / "dyes-template", assets / "dyes-template")
        (assets / "paper-template").mkdir()
        shutil.copy2(templates.ASSET_DIR / "paper-template/examples.tex", assets / "paper-template/examples.tex")
        shutil.copy2(templates.ASSET_DIR / "prism-cjk.sty", assets / "prism-cjk.sty")
        target = self.root / "preserve"
        target.mkdir()
        (target / "keep.txt").write_text("synthetic content")
        before = self.inventory(target)
        for name in ("common/supplementary.tex", "common/references.bib", "common/NOTICE.md",
                     "common/graphical_abstract.tex", "common/highlights.txt", "review/main.tex"):
            with self.subTest(resource=name):
                path = assets / "dyes-template" / name
                contents = path.read_bytes()
                path.unlink()
                try:
                    with mock.patch.object(templates, "ASSET_DIR", assets):
                        with self.assertRaisesRegex(SystemExit, "missing"):
                            self.initialize(target, article_type="review", force=True)
                    self.assertEqual(self.inventory(target), before)
                    self.assertFalse(target.with_name(target.name + ".backup").exists())
                finally:
                    path.write_bytes(contents)

    def test_real_main_supplements_and_auxiliary_documents(self):
        require_tex(self, ("elsarticle.cls", "elsarticle-num.bst", "newfloat.sty", "mhchem.sty",
                           "xeCJK.sty", "FandolSong-Regular.otf"))
        for language in ("bilingual", "english"):
            for kind in ("research", "review"):
                with self.subTest(language=language, kind=kind):
                    project = self.root / "编译项目" / language / kind
                    self.initialize(project, article_type=kind, language=language)
                    self.assert_success(self.cli(project, "--strict", timeout=300))
                    rebuild = project / "prism-build.sh"
                    old_script = rebuild.read_bytes()
                    for name in ("supplementary.tex",):
                        self.assert_success(self.cli(project, "--main", name, "--strict", "--no-build-script", timeout=300))
                        text = self.text_of(project / (name.removesuffix(".tex") + ".pdf"))
                        self.assertRegex(text, r"S1")
                    if kind == "research":
                        for name in ("examples.tex", "graphical_abstract.tex"):
                            self.assert_success(self.cli(project, "--main", name, "--strict", "--no-build-script", timeout=300))
                    self.assertEqual(rebuild.read_bytes(), old_script)
                    self.assert_clean(project)

    def test_real_citation_order_and_doi_links_preserve_old_pdf_on_error(self):
        require_tex(self, ("elsarticle.cls", "elsarticle-num.bst", "newfloat.sty", "mhchem.sty"))
        if not shutil.which("pdftohtml"):
            self.skipTest("DOI link check requires pdftohtml")
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
            + "}, journal={Synthetic Journal}, year={2026}, volume={2}, pages={11--19},"
            + " doi={10.0000/prism-dyes-" + key + "}}"
            for key, title in (("alpha", "Complete Alpha Article Title"), ("zulu", "Complete Zulu Article Title"))))
        args = (project, "--main", fixture.name, "--strict", "--no-build-script")
        self.assert_success(self.cli(*args))
        pdf = fixture.with_suffix(".pdf")
        text = " ".join(self.text_of(pdf, "-raw").split())
        self.assertRegex(text, r"FirstMarker\s*\[1\];\s*SecondMarker\s*\[2\]\.")
        self.assertLess(text.casefold().index("complete zulu article title"),
                        text.casefold().index("complete alpha article title"))
        html = subprocess.run(["pdftohtml", "-stdout", "-i", "-noframes", str(pdf)],
                              capture_output=True, text=True, check=True, timeout=30).stdout
        for key in ("alpha", "zulu"):
            self.assertIn('href="https://doi.org/10.0000/prism-dyes-' + key + '"', html)
        previous = pdf.read_bytes()
        fixture.write_text(document.replace(r"\end{document}", r"\UndefinedSyntheticFixture" + "\n" + r"\end{document}"))
        self.assertNotEqual(self.cli(*args).returncode, 0)
        self.assertEqual(pdf.read_bytes(), previous)
        self.assert_clean(project)


if __name__ == "__main__":
    unittest.main()
