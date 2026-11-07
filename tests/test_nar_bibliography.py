"""Exercise Prism's NAR bibliography adaptation with real BibTeX output."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "skills/paper-latex/assets/nar-template/common/prism-nar.bst"
BIBTEX = shutil.which("bibtex")


@unittest.skipUnless(BIBTEX, "BibTeX is required for bibliography integration tests")
class NarBibliographyTests(unittest.TestCase):
    def render(self, records: str, citations: tuple[str, ...]) -> tuple[str, dict[str, str]]:
        with tempfile.TemporaryDirectory(prefix="prism-nar-bib-") as temporary:
            directory = Path(temporary)
            shutil.copy2(STYLE, directory / STYLE.name)
            (directory / "fixture.bib").write_text(records, encoding="utf-8")
            (directory / "fixture.aux").write_text(
                "\\relax\n\\citation{" + ",".join(citations)
                + "}\n\\bibstyle{prism-nar}\n\\bibdata{fixture}\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [BIBTEX, "fixture"], cwd=directory,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertNotIn("Warning--", result.stdout, result.stdout)
            bibliography = (directory / "fixture.bbl").read_text(encoding="utf-8")
        parts = re.split(r"\\bibitem\{([^}]+)\}", bibliography)
        entries = {
            parts[index]: " ".join(parts[index + 1].split())
            for index in range(1, len(parts), 2)
        }
        return bibliography, entries

    def test_citation_order_complete_titles_and_author_boundaries(self):
        bibliography, entries = self.render(r"""
@article{alpha,
  author = {Alpha, Alice and Beta, Bob and Gamma, Grace},
  title = {Complete Three Author Title with {DNA} and {RNA}},
  journal = {Synthetic Journal}, year = {2026}, volume = {2}, pages = {3--4}
}
@article{zeta,
  author = {Zeta, Zoe and Yankee, Yann and Xray, Xena and Whiskey, William},
  title = {Complete Four Author Title with {ATP} and {PCR}},
  journal = {Synthetic Journal}, year = {2026}, volume = {1}, pages = {1--2}
}
""", ("zeta", "alpha"))
        self.assertEqual(re.findall(r"\\bibitem\{([^}]+)\}", bibliography), ["zeta", "alpha"])
        self.assertIn("Zeta~Z, Yankee~Y, Xray~X et~al.", entries["zeta"])
        self.assertNotIn("Whiskey", entries["zeta"])
        self.assertNotIn("Zoe", entries["zeta"])
        self.assertIn("Alpha~A, Beta~B and Gamma~G", entries["alpha"])
        self.assertNotIn("et~al.", entries["alpha"])
        self.assertIn("Complete Four Author Title with {ATP} and {PCR}", entries["zeta"])
        self.assertIn("Complete Three Author Title with {DNA} and {RNA}", entries["alpha"])

    def test_active_doi_and_pmc_links_with_pubmed_fallback(self):
        _, entries = self.render(r"""
@article{pmc,
  author = {Example, Alice}, title = {Synthetic PMC link record},
  journal = {Synthetic Journal}, year = {2026}, volume = {1}, pages = {1},
  doi = {10.0000/synthetic}, pmcid = {PMC123456}, pmid = {654321},
  url = {https://example.org/duplicate}
}
@article{pmid,
  author = {Example, Bob}, title = {Synthetic PubMed link record},
  journal = {Synthetic Journal}, year = {2026}, volume = {1}, pages = {2},
  pmid = {765432}
}
@article{empty,
  author = {Example, Carol}, title = {Synthetic record without identifiers},
  journal = {Synthetic Journal}, year = {2026}, volume = {1}, pages = {3}
}
""", ("pmc", "pmid", "empty"))
        self.assertIn(r"\href{https://doi.org/10.0000/synthetic}", entries["pmc"])
        self.assertIn(r"\href{https://pmc.ncbi.nlm.nih.gov/articles/PMC123456/}{PMC123456}", entries["pmc"])
        self.assertNotIn("pubmed.ncbi", entries["pmc"])
        self.assertNotIn("example.org/duplicate", entries["pmc"])
        self.assertIn(r"\href{https://pubmed.ncbi.nlm.nih.gov/765432/}{PubMed: 765432}", entries["pmid"])
        self.assertNotIn("pmc.ncbi", entries["pmid"])
        self.assertNotIn(r"\href", entries["empty"])
        self.assertNotIn(r"\url", entries["empty"])

    def test_identifier_normalization_and_url_only_records(self):
        _, entries = self.render(r"""
@misc{numericpmc,
  author = {Example, Alice}, title = {Numeric PMC identifier}, year = {2026},
  pmcid = {123456}, doi = {https://doi.org/10.0000/numeric}
}
@misc{lowerpmc,
  author = {Example, Bob}, title = {Lowercase PMC identifier}, year = {2026},
  pmcid = {pmc234567}, doi = {doi:10.0000/lower}
}
@misc{dxdoi,
  author = {Example, Carol}, title = {Legacy DOI URL}, year = {2026},
  doi = {https://dx.doi.org/10.0000/legacy}
}
@misc{urlonly,
  author = {{Synthetic Resource Consortium}}, title = {Synthetic URL record},
  year = {2026}, url = {https://example.org/resource}
}
""", ("numericpmc", "lowerpmc", "dxdoi", "urlonly"))
        self.assertIn("articles/PMC123456/", entries["numericpmc"])
        self.assertIn("articles/PMC234567/", entries["lowerpmc"])
        self.assertIn(r"\href{https://doi.org/10.0000/numeric}", entries["numericpmc"])
        self.assertIn(r"\href{https://doi.org/10.0000/lower}", entries["lowerpmc"])
        self.assertIn(r"\href{https://doi.org/10.0000/legacy}", entries["dxdoi"])
        self.assertNotIn("doi.org/https", " ".join(entries.values()))
        self.assertIn(r"\url{https://example.org/resource}", entries["urlonly"])
        self.assertIn("Synthetic Resource Consortium", entries["urlonly"])

    def test_books_chapters_preprints_data_and_software_keep_their_fields(self):
        _, entries = self.render(r"""
@book{book,
  author = {Example, Alice}, title = {Synthetic Book},
  publisher = {Example Press}, address = {Example City}, year = {2026}
}
@incollection{chapter,
  author = {Example, Bob}, title = {Synthetic Chapter},
  editor = {Example, Carol}, booktitle = {Synthetic Collected Work},
  publisher = {Example Press}, year = {2026}, pages = {10--20}
}
@preprint{preprint,
  author = {Example, David}, title = {Synthetic Preprint}, year = {2026},
  note = {Preprint: not peer reviewed}, doi = {10.0000/preprint}
}
@dataset{data,
  author = {Example, Eve}, title = {Synthetic Dataset}, year = {2026},
  howpublished = {Example Repository}, doi = {10.0000/data}
}
@software{software,
  author = {Example, Fran}, title = {Synthetic Software}, year = {2026},
  note = {Version 1.0}, url = {https://example.org/software}
}
""", ("book", "chapter", "preprint", "data", "software"))
        self.assertIn("Synthetic Book", entries["book"])
        self.assertIn("Example Press", entries["book"])
        self.assertIn("Synthetic Collected Work", entries["chapter"])
        self.assertIn("10--20", entries["chapter"])
        self.assertIn("Preprint: not peer reviewed", entries["preprint"])
        self.assertIn("Example Repository", entries["data"])
        self.assertIn("10.0000/data", entries["data"])
        self.assertIn("Version 1.0", entries["software"])
        self.assertIn(r"\url{https://example.org/software}", entries["software"])


if __name__ == "__main__":
    unittest.main()
