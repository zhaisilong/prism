"""Catalog-driven initialization and real build contracts for every profile."""

from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path
import sys
import unittest

from prism_test_support import ROOT, TemplateSupport, require_tex, inventory, pdf_text
sys.path.insert(0, str(ROOT / "scripts/lib"))
from prism_latex.catalog import CATALOG


class TemplateContractTests(TemplateSupport, unittest.TestCase):
    def test_every_registered_content_profile_and_language_builds_cleanly(self):
        require_tex(self, ("xeCJK.sty", "FandolSong-Regular.otf", "achemso.sty", "elsarticle.cls"))
        jobs = [(record, kind, language)
                for record in CATALOG.templates.values()
                for kind in record.article_types or (None,)
                for language in ("bilingual", "english")]

        def check(job):
            record, kind, language = job
            project = self.root / "模板 contracts" / record.alias / (kind or "default") / language
            self.initialize(project, template=record.id, article_type=kind, language=language)
            metadata = json.loads((project / "prism-template.json").read_text())
            self.assertEqual(metadata["schema_version"], 1)
            self.assertEqual(metadata["template_id"], record.id)
            sources = inventory(project)
            # Shared examples need one real build per venue/language, rather
            # than repeating them for every content skeleton of that venue.
            documents = {role.path for role in record.documents if role.standalone
                         and (role.role != "examples" or kind in (None, record.article_type))}
            self.assertIn("main.tex", documents)
            self.assert_success(self.cli(project, "--strict"), f"{record.alias}/{kind}/{language}/main")
            script = project / "prism-build.sh"
            self.assertTrue(script.is_file())
            script_bytes = script.read_bytes()
            for name in sorted(documents):
                if name != "main.tex":
                    self.assert_success(self.cli(project, "--main", name, "--strict", "--no-build-script"),
                                        f"{record.alias}/{kind}/{language}/{name}")
                pdf = project / Path(name).with_suffix(".pdf")
                self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))
                self.assertTrue(pdf_text(pdf).strip(), str(pdf))
            self.assertEqual(script.read_bytes(), script_bytes)
            after = inventory(project)
            for name, data in sources.items():
                self.assertEqual(after[name], data, name)
            self.assert_clean(project)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results = {pool.submit(check, job): (job[0].alias, job[1], job[2]) for job in jobs}
            for future in concurrent.futures.as_completed(results):
                with self.subTest(profile=results[future]):
                    future.result()


if __name__ == "__main__":
    unittest.main()
