"""Observable contracts for the generic Prism manuscript starter."""

import subprocess
import re
import unittest

from prism_test_support import TemplateSupport, inventory, pdf_text, require_tex


class PrismLayoutTests(TemplateSupport, unittest.TestCase):
    def test_initialization_refuses_existing_manuscript_without_changes(self):
        project = self.root / "已有稿件 with spaces"
        project.mkdir()
        (project / "main.tex").write_text("% Existing manuscript 中文\n", encoding="utf-8")
        (project / "prism-paper.sty").write_text("% User's previous style\n", encoding="utf-8")
        (project / "references.bib").write_text("% User bibliography\n", encoding="utf-8")
        before = inventory(project)
        result = self.cli("--init", project, "--template", "prism")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(inventory(project), before)

    def test_supplement_independent_numbering_and_rebuild_entrypoint(self):
        require_tex(self, ("xeCJK.sty", "FandolSong-Regular.otf", "luatexja-fontspec.sty"),
                    commands=("xelatex", "lualatex", "latexmk", "bibtex", "kpsewhich", "pdftotext"))
        cache = self.root / "font cache"
        cache.mkdir()
        self.env.update(TEXMFCACHE=str(cache), TEXMFVAR=str(cache), XDG_CACHE_HOME=str(cache))
        for engine in ("xelatex", "lualatex"):
            with self.subTest(engine=engine):
                project = self.root / ("补充材料 " + engine)
                self.assert_success(self.cli("--init", project, "--template", "prism"))
                self.assert_success(self.cli(project, "--engine", engine, "--strict", timeout=300))
                rebuild = project / "prism-build.sh"
                self.assertTrue(rebuild.is_file())
                original = rebuild.read_bytes()
                source = project / "supplementary.tex"
                text = source.read_text(encoding="utf-8")
                source.write_text(text.replace(r"\end{document}", "中文补充材料。\n" + r"\end{document}"), encoding="utf-8")
                self.assert_success(self.cli(project, "--engine", engine, "--main", source.name,
                                             "--strict", "--no-build-script", timeout=300))
                content = pdf_text(project / "supplementary.pdf")
                self.assertIn("Contents", content)
                self.assertRegex(content, r"Figure\s+S1")
                self.assertRegex(content, r"Table\s+S1")
                self.assertIn("(S1)", content)
                references = content.rfind("Supplementary references")
                self.assertGreater(references, list(re.finditer(r"Figure\s+S1", content))[-1].start())
                self.assertGreater(references, list(re.finditer(r"Table\s+S1", content))[-1].start())
                self.assertNotRegex(content, r"(?m)^\s*References\s*$")
                # Bound pagination only for this unchanged synthetic fixture.
                self.assertGreaterEqual(content.count("\f"), 2)
                self.assertLessEqual(content.count("\f"), 4)
                self.assertIn("中文补充材料", content)
                self.assertIn("S1", subprocess.run(
                    ["pdftotext", "-f", "1", "-l", "1", str(project / "supplementary.pdf"), "-"],
                    check=True, capture_output=True, text=True, timeout=30).stdout)
                self.assertEqual(rebuild.read_bytes(), original)
                self.assert_clean(project)


if __name__ == "__main__":
    unittest.main()
