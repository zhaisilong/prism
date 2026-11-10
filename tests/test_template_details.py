"""Read-only maintenance CLI and single metadata-read contracts."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from prism_test_support import ROOT, TemplateSupport, inventory
sys.path.insert(0, str(ROOT / "scripts/lib"))
from prism_latex import paper, catalog, notes, reviewer


class TemplateDetailsTests(TemplateSupport, unittest.TestCase):
    def query(self, *args):
        env = dict(self.env, PATH="", PYTHONPATH=str(ROOT / "scripts/lib"))
        return subprocess.run([sys.executable, "-B", "-m", "prism_latex.catalog_cli", *args],
                              env=env, cwd=self.root, text=True, capture_output=True, timeout=30)

    def test_all_details_are_versioned_relative_and_do_not_read_a_project(self):
        (self.root / "prism-template.json").write_text("malformed local metadata")
        before = inventory(self.root)
        for alias in catalog.CATALOG.templates:
            with self.subTest(template=alias):
                result = self.query("--show", alias, "--json")
                self.assert_success(result)
                detail = json.loads(result.stdout)
                self.assertEqual(detail["schema_version"], 1)
                self.assertEqual(detail["alias"], alias)
                for key in ("guide_path", "asset_path"):
                    self.assertFalse(Path(detail[key]).is_absolute())
                    self.assertNotIn("..", Path(detail[key]).parts)
                    self.assertTrue((ROOT / detail[key]).exists())
                self.assertIn("main", [item["role"] for item in detail["documents"]])
                for item in detail["documents"]:
                    self.assertFalse(Path(item["path"]).is_absolute())
                self.assertEqual(detail["capabilities"]["article_type_selection"],
                                 len(detail["article_types"]) > 1)
                alias_result = self.query("--show", detail["id"], "--json")
                self.assertEqual(result.stdout, alias_result.stdout)
                human = self.query("--show", alias)
                self.assert_success(human)
                self.assertIn(detail["guide_path"], human.stdout)
                for source in detail["sources"]:
                    self.assertIn(source["url"], human.stdout)
        self.assertEqual(inventory(self.root), before)

    def test_validation_is_offline_without_tex_and_nonmutating(self):
        before = inventory(self.root)
        result = self.query("--validate")
        self.assert_success(result)
        self.assertIn("16 templates", result.stdout)
        self.assertEqual(inventory(self.root), before)

    def test_invalid_queries_are_rejected_without_mutation(self):
        for arguments in (("--json",), ("--show", "missing"),
                          ("--show", "prism", "--validate"),
                          ("--show", "prism", "--group-by", "none"),
                          ("--validate", "--group-by", "publisher")):
            with self.subTest(arguments=arguments):
                result = self.query(*arguments)
                self.assertNotEqual(result.returncode, 0)
        self.assertEqual(inventory(self.root), {})

    def test_paper_dependency_command_reads_metadata_exactly_once(self):
        project = self.root / "paper"
        self.initialize(project, template="advanced-science")
        metadata = project / "prism-template.json"
        original = Path.read_text
        reads = []

        def read(path, *args, **kwargs):
            if path == metadata:
                reads.append(path)
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", read), \
                mock.patch.object(paper, "dependency_report", return_value=(True, [])), \
                mock.patch.object(paper.shutil, "which", return_value="bibtex"), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(paper.main([str(project), "--check-deps"]), 0)
        self.assertEqual(reads, [metadata])

    def test_all_workflows_use_the_same_executor_and_publisher(self):
        self.assertIs(paper.execute_build, notes.execute_build)
        self.assertIs(paper.execute_build, reviewer.execute_build)
        self.assertIs(paper.publish_artifacts, notes.publish_artifacts)
        self.assertIs(paper.publish_artifacts, reviewer.publish_artifacts)


if __name__ == "__main__":
    unittest.main()
