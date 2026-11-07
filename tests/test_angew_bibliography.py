"""Verify the renamed Angew bibliography style using actual BibTeX output."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "skills/paper-latex/assets/angew-template/common/prism-angew.bst"
BIBTEX = shutil.which("bibtex")


@unittest.skipUnless(BIBTEX, "BibTeX is required for bibliography integration tests")
class AngewBibliographyTests(unittest.TestCase):
    def render(self, records, citations):
        with tempfile.TemporaryDirectory(prefix="prism-angew-bib-") as temporary:
            root = Path(temporary)
            shutil.copy2(STYLE, root / STYLE.name)
            (root / "fixture.bib").write_text(records, encoding="utf-8")
            (root / "fixture.aux").write_text(
                "\\relax\n\\citation{" + ",".join(citations)
                + "}\n\\bibstyle{prism-angew}\n\\bibdata{fixture}\n",
                encoding="utf-8",
            )
            result = subprocess.run([BIBTEX, "fixture"], cwd=root,
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("Warning--", result.stdout)
            bibliography = (root / "fixture.bbl").read_text()
        parts = re.split(r"\\bibitem\{([^}]+)\}", bibliography)
        entries = {parts[i]: " ".join(parts[i + 1].split())
                   for i in range(1, len(parts), 2)}
        return bibliography, entries

    def test_six_authors_are_listed_and_seven_use_the_first_three(self):
        bibliography, entries = self.render(r"""
@article{alpha,
  author={Alpha, Alice and Beta, Bob and Gamma, Grace and Delta, Dan and Epsilon, Eve and Zeta, Zoe},
  title={Complete Six Author Article Title with {DNA}},
  journal={Full Synthetic Journal Name}, year={2026}, volume={2}, pages={3--4}
}
@article{zeta,
  author={Zeta, Zoe and Yankee, Yann and Xray, Xena and Whiskey, Will and Victor, Vera and Uniform, Una and Tango, Tom},
  title={Complete Seven Author Article Title with {ATP}},
  journal={Another Full Synthetic Journal Name}, year={2026}, volume={1}, pages={1--2}
}
""", ("zeta", "alpha"))
        self.assertEqual(re.findall(r"\\bibitem\{([^}]+)\}", bibliography), ["zeta", "alpha"])
        for author in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"):
            self.assertIn(author, entries["alpha"])
        self.assertNotIn("et~al.", entries["alpha"])
        self.assertIn("A.~Alpha", entries["alpha"])
        self.assertIn("Z.~Zeta, Y.~Yankee, X.~Xray et~al.", entries["zeta"])
        for author in ("Whiskey", "Victor", "Uniform", "Tango"):
            self.assertNotIn(author, entries["zeta"])
        self.assertIn("Complete Six Author Article Title with {DNA}", entries["alpha"])
        self.assertIn("Another Full Synthetic Journal Name", entries["zeta"])

    def test_doi_article_numbers_and_pages_are_preserved(self):
        _, entries = self.render(r"""
@article{eid,
  author={Example, Alice}, title={Synthetic Article with an Electronic Locator},
  journal={Full Synthetic Journal Name}, year={2026}, volume={7},
  eid={e202600001}, doi={https://doi.org/10.0000/synthetic-eid}
}
@article{pages,
  author={Example, Bob}, title={Synthetic Article with Pagination},
  journal={Full Synthetic Journal Name}, year={2026}, volume={8},
  pages={e202600002}, eid={do-not-duplicate}, doi={10.0000/synthetic-pages}
}
@misc{software,
  author={{Synthetic Software Consortium}}, title={Synthetic Software Entry},
  year={2026}, note={Version 1.0}, url={https://example.org/software}
}
""", ("eid", "pages", "software"))
        self.assertIn("e202600001", entries["eid"])
        self.assertIn(r"\href{https://doi.org/10.0000/synthetic-eid}", entries["eid"])
        self.assertIn("e202600002", entries["pages"])
        self.assertNotIn("do-not-duplicate", entries["pages"])
        self.assertIn(r"\href{https://doi.org/10.0000/synthetic-pages}", entries["pages"])
        self.assertIn(r"\url{https://example.org/software}", entries["software"])
        self.assertNotIn("doi.org/https", " ".join(entries.values()))


if __name__ == "__main__":
    unittest.main()
