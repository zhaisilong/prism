"""JMC and EJMC contracts using temporary synthetic manuscripts only."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest import mock
import urllib.request
import xml.etree.ElementTree as ET

from prism_test_support import ROOT, TemplateSupport, require_tex
sys.path.insert(0, str(ROOT / "scripts/lib"))
from prism_latex import templates
from prism_latex.catalog import CATALOG


VENUES = {
    "jmc": ("journal/journal-of-medicinal-chemistry", "ACS", ("research", "perspective")),
    "ejmc": ("journal/european-journal-of-medicinal-chemistry", "Elsevier", ("research", "review")),
}


class MedicinalChemistryTests(TemplateSupport, unittest.TestCase):
    def test_all_profiles_initialize_offline_in_chinese_paths_with_both_languages(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network")) as fetch:
            for alias, (canonical, publisher, kinds) in VENUES.items():
                for language in ("bilingual", "english"):
                    for kind in kinds:
                        with self.subTest(template=alias, language=language, article_type=kind):
                            project = self.root / "中文 manuscript paths" / alias / language / kind
                            self.initialize(project, template=canonical if language == "english" else alias,
                                            article_type=kind, language=language)
                            metadata = json.loads((project / templates.METADATA_NAME).read_text())
                            self.assertEqual(metadata["schema_version"], 1)
                            self.assertEqual(metadata["template"], alias)
                            self.assertEqual(metadata["template_id"], canonical)
                            self.assertEqual(metadata["article_type"], kind)
                            self.assertEqual(metadata["language"], language)
                            self.assertEqual(metadata["engine"], "xelatex" if language == "bilingual" else "pdflatex")
                            self.assertNotIn(str(self.root), json.dumps(metadata))
                            expected = {"main.tex", "supplementary.tex", "examples.tex"}
                            if alias == "ejmc":
                                expected.add("graphical_abstract.tex")
                                self.assertTrue((project / "highlights.txt").is_file())
                            self.assertEqual({p.name for p in project.glob("*.tex")}, expected)
                            for name in expected:
                                self.assertEqual(r"\usepackage{prism-cjk}" in (project / name).read_text(),
                                                 language == "bilingual", name)
                            self.assertFalse(any((project / item).exists() for item in (*kinds, "common")))
                            self.assertFalse(list(project.glob("*.zip")))
                            if language == "english":
                                source = templates.ASSET_DIR / (alias + "-template") / kind / "main.tex"
                                self.assertEqual((project / "main.tex").read_bytes(), source.read_bytes())
                            self.assert_clean(project)
        fetch.assert_not_called()

    def test_catalog_groups_details_and_engine_preview_remain_read_only(self):
        env = dict(self.env, PATH="")
        listing = self.cli("--list-templates", "--group-by", "publisher", env=env)
        self.assert_success(listing)
        for alias, (canonical, publisher, kinds) in VENUES.items():
            with self.subTest(template=alias):
                block = listing.stdout.split("\n" + publisher + "\n", 1)[1].split("\n\n", 1)[0]
                self.assertIn(alias + ":", block)
                self.assertIn(canonical, block)
                detail = CATALOG.detail(alias)
                self.assertEqual(detail["publisher"], publisher)
                self.assertEqual(detail["article_types"], list(kinds))
                self.assertEqual(detail["default_article_type"], "research")
                self.assertTrue(detail["capabilities"]["article_type_selection"])
                self.assertFalse(detail["capabilities"]["official_package_import"])
                self.assertNotIn("highlights.txt", {item["path"] for item in detail["documents"]})
                role = "toc_graphic" if alias == "jmc" else "graphical_abstract"
                special = next(item for item in detail["documents"] if item["role"] == role)
                self.assertEqual(special["standalone"], alias == "ejmc")
                project = self.root / alias
                self.initialize(project, template=alias, article_type=kinds[1])
                before = self.inventory(project)
                preview = self.cli(project, "--check-deps", env=env)
                self.assertNotEqual(preview.returncode, 0)
                for dependency in ("xelatex: MISSING", "mhchem.sty: MISSING", "newfloat.sty: MISSING"):
                    self.assertIn(dependency, preview.stdout)
                english = self.cli("--check-deps", "--template", canonical, "--language", "english", env=env)
                self.assertIn("pdflatex: MISSING", english.stdout)
                self.assertNotIn("xeCJK.sty", english.stdout)
                self.assertIn("achemso.sty" if alias == "jmc" else "elsarticle.cls", english.stdout)
                self.assertEqual(self.inventory(project), before)

    def test_default_and_legacy_article_metadata_are_read_only(self):
        for alias, (_, _, kinds) in VENUES.items():
            project = self.root / alias
            self.initialize(project, template=alias)
            path = project / templates.METADATA_NAME
            metadata = json.loads(path.read_text())
            self.assertEqual(metadata.pop("article_type"), "research")
            original = (json.dumps(metadata) + "\n").encode()
            path.write_bytes(original)
            self.assertEqual(templates.template_article_type_for_project(project), "research")
            self.assertEqual(path.read_bytes(), original)
            for invalid in ("review" if alias == "jmc" else "perspective", [], None):
                with self.subTest(template=alias, invalid=invalid):
                    bad = json.dumps(dict(metadata, article_type=invalid)).encode()
                    path.write_bytes(bad)
                    with self.assertRaisesRegex(SystemExit, "Invalid Prism template metadata"):
                        templates.template_for_project(project)
                    self.assertEqual(path.read_bytes(), bad)

    def test_invalid_options_and_official_source_import_never_mutate_targets(self):
        target = self.root / "existing author material"
        target.mkdir()
        (target / "preserve.txt").write_bytes(b"synthetic local author material")
        before = self.inventory(target)
        for alias, (_, _, kinds) in VENUES.items():
            for extra in (("--article-type", "review" if alias == "jmc" else "perspective"),
                          ("--template-source", self.root / "unopened.zip"),
                          ("--language", "unknown"), ("--engine", "lualatex")):
                with self.subTest(template=alias, extra=extra):
                    result = self.cli("--init", target, "--force", "--template", alias, *extra)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(self.inventory(target), before)
                    self.assertFalse(list(self.root.glob(target.name + ".backup*")))
            missing = self.root / "not created" / alias
            result = self.cli("--init", missing, "--template", alias, "--article-type", "database")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(missing.parent.exists())
        result = self.cli(target, "--article-type", "research")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.inventory(target), before)

    def test_force_backs_up_the_complete_previous_content(self):
        for alias, (_, _, kinds) in VENUES.items():
            project = self.root / (alias + " 原稿")
            self.initialize(project, template=alias, language="english")
            (project / "local.txt").write_text("synthetic author notes")
            before = self.inventory(project)
            with self.assertRaisesRegex(SystemExit, "not empty"):
                self.initialize(project, template=alias, article_type=kinds[1])
            self.assertEqual(self.inventory(project), before)
            self.initialize(project, template=alias, article_type=kinds[1], force=True)
            self.assertEqual(self.inventory(project.with_name(project.name + ".backup")), before)
            self.assertEqual(templates.template_article_type_for_project(project), kinds[1])
            self.assertFalse((project / "local.txt").exists())

    def test_missing_selected_and_shared_resources_fail_before_target_changes(self):
        assets = self.root / "controlled public assets"
        assets.mkdir()
        for alias in VENUES:
            shutil.copytree(templates.ASSET_DIR / (alias + "-template"), assets / (alias + "-template"))
        (assets / "paper-template").mkdir()
        shutil.copy2(templates.ASSET_DIR / "paper-template/examples.tex", assets / "paper-template/examples.tex")
        shutil.copy2(templates.ASSET_DIR / "prism-cjk.sty", assets / "prism-cjk.sty")
        target = self.root / "existing target"
        target.mkdir()
        (target / "keep.txt").write_text("synthetic author material")
        before = self.inventory(target)
        for alias, (_, _, kinds) in VENUES.items():
            files = ["common/supplementary.tex", "common/references.bib", "common/NOTICE.md", kinds[1] + "/main.tex"]
            if alias == "ejmc":
                files.extend(("common/graphical_abstract.tex", "common/highlights.txt"))
            for relative in files:
                with self.subTest(template=alias, resource=relative):
                    path = assets / (alias + "-template") / relative
                    content = path.read_bytes()
                    path.unlink()
                    try:
                        with mock.patch.object(templates, "ASSET_DIR", assets):
                            with self.assertRaisesRegex(SystemExit, "missing"):
                                self.initialize(target, template=alias, article_type=kinds[1], force=True)
                        self.assertEqual(self.inventory(target), before)
                        self.assertFalse(list(self.root.glob(target.name + ".backup*")))
                    finally:
                        path.write_bytes(content)


class MedicinalBibliographyTests(TemplateSupport, unittest.TestCase):
    def prepare(self, alias):
        require_tex(self, ("achemso.sty", "elsarticle.cls", "newfloat.sty", "mhchem.sty"))
        if not shutil.which("pdftohtml"):
            self.skipTest("DOI link checks require pdftohtml")
        project = self.root / alias
        self.initialize(project, template=alias, language="english")
        main = (project / "main.tex").read_text()
        preamble = main.split(r"\begin{document}", 1)[0]
        bibliography_style = re.search(r"\\bibliographystyle\{[^}]+\}", main)
        style = bibliography_style.group() + "\n" if bibliography_style else ""
        fixture = project / "citation-check.tex"
        citations = (r"FirstMarker\cite{zulu}; SecondMarker\cite{alpha}." if alias == "jmc" else
                     r"FirstMarker \cite{zulu}; SecondMarker \cite{alpha}.")
        document = (preamble + "\n" + r"\begin{document}" + "\n" + citations + "\n"
                    + style + r"\bibliography{fixture}" + "\n" + r"\end{document}" + "\n")
        fixture.write_text(document)
        return project, fixture, document

    def assert_links_and_sources(self, pdf, project, before, prefix):
        html = subprocess.run(["pdftohtml", "-stdout", "-i", "-noframes", str(pdf)],
                              capture_output=True, text=True, check=True, timeout=30).stdout
        for key in ("alpha", "zulu"):
            self.assertIn('href="https://doi.org/10.0000/' + prefix + key + '"', html)
        for relative, content in before.items():
            self.assertEqual((project / relative).read_bytes(), content)
        self.assert_clean(project)

    def test_jmc_real_preamble_author_boundary_super_citations_and_acs_isolation(self):
        project, fixture, document = self.prepare("jmc")
        fifteen = ["Fiv" + chr(ord("A") + i) for i in range(15)]
        sixteen = ["Six" + chr(ord("A") + i) for i in range(16)]
        records = []
        for key, authors, title in (("alpha", fifteen, "Complete Fifteen Author Title"),
                                    ("zulu", sixteen, "Complete Sixteen Author Title")):
            records.append("@article{" + key + ", author={" + " and ".join(name + ", Alice" for name in authors)
                           + "}, title={" + title + "}, journal={Synth. J.}, year={2026}, volume={2},"
                           + " pages={11--19}, doi={10.0000/prism-jmc-" + key + "}}\n")
        (project / "fixture.bib").write_text("\n".join(records))
        sentinel = project / "acs-citation-check.bib"
        sentinel.write_text("@Control{achemso-control,ctrl-article-title={no}}\n"
                            "@article{sourceOnlySentinel,author={Sentinel, Alice},title={Source only},"
                            "journal={Synth. J.},year={2026}}\n")
        before = self.inventory(project)
        args = (project, "--main", fixture.name, "--strict", "--no-build-script")
        self.assert_success(self.cli(*args))
        pdf = fixture.with_suffix(".pdf")
        text = " ".join(self.text_of(pdf, "-raw").split())
        self.assertLess(text.index("Complete Sixteen Author Title"), text.index("Complete Fifteen Author Title"))
        first = text.split("(1)", 1)[1].split("(2)", 1)[0]
        second = text.split("(2)", 1)[1]
        self.assertIn(sixteen[0], first)
        for omitted in sixteen[1:]:
            self.assertNotIn(omitted, first)
        self.assertIn("et al.", first)
        for author in fifteen:
            self.assertIn(author, second)
        self.assertNotIn("et al.", second)
        words = list(ET.fromstring(self.text_of(pdf, "-bbox")).iter("{http://www.w3.org/1999/xhtml}word"))
        for marker, number in (("FirstMarker;", "1"), ("SecondMarker.", "2")):
            index = next(i for i, word in enumerate(words) if word.text == marker)
            citation = next(word for word in words[index + 1:index + 4] if word.text == number)
            self.assertLess(float(citation.attrib["yMax"]), float(words[index].attrib["yMax"]) - 1)
        self.assert_links_and_sources(pdf, project, before, "prism-jmc-")
        previous = pdf.read_bytes()
        fixture.write_text(document.replace(r"\bibliography", r"Unresolved \cite{sourceOnlySentinel}." + "\n" + r"\bibliography", 1))
        failure = self.cli(*args)
        self.assertNotEqual(failure.returncode, 0)
        self.assertEqual(pdf.read_bytes(), previous)
        self.assertEqual(sentinel.read_bytes(), before[sentinel.name])
        self.assert_clean(project)

    def test_ejmc_real_preamble_inline_square_citation_order_and_doi_links(self):
        project, fixture, document = self.prepare("ejmc")
        records = []
        for key, title in (("alpha", "Complete Alpha Article Title"), ("zulu", "Complete Zulu Article Title")):
            records.append("@article{" + key + ", author={Example, Alice}, title={" + title
                           + "}, journal={Synthetic Journal}, year={2026}, volume={2}, pages={11--19},"
                           + " doi={10.0000/prism-ejmc-" + key + "}}\n")
        (project / "fixture.bib").write_text("\n".join(records))
        before = self.inventory(project)
        args = (project, "--main", fixture.name, "--strict", "--no-build-script")
        self.assert_success(self.cli(*args))
        pdf = fixture.with_suffix(".pdf")
        text = " ".join(self.text_of(pdf, "-raw").split())
        self.assertRegex(text, r"FirstMarker\s*\[1\];\s*SecondMarker\s*\[2\]\.")
        normalized = text.casefold()
        self.assertLess(normalized.index("complete zulu article title"), normalized.index("complete alpha article title"))
        words = list(ET.fromstring(self.text_of(pdf, "-bbox")).iter("{http://www.w3.org/1999/xhtml}word"))
        for marker, number in (("FirstMarker", "[1];"), ("SecondMarker", "[2].")):
            index = next(i for i, word in enumerate(words) if word.text == marker)
            citation = next(word for word in words[index + 1:index + 4] if word.text == number)
            self.assertLess(abs(float(citation.attrib["yMax"]) - float(words[index].attrib["yMax"])), 1)
        self.assert_links_and_sources(pdf, project, before, "prism-ejmc-")
        previous = pdf.read_bytes()
        fixture.write_text(document.replace(r"\end{document}", r"\UndefinedSyntheticFixture" + "\n" + r"\end{document}", 1))
        self.assertNotEqual(self.cli(*args).returncode, 0)
        self.assertEqual(pdf.read_bytes(), previous)
        self.assert_clean(project)


if __name__ == "__main__":
    unittest.main()
