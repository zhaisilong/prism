from __future__ import annotations

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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from prism_latex import templates

PAPER = ROOT / "scripts" / "latex-paper.sh"
CATALOG = ROOT / "scripts" / "latex-templates.sh"


class CatalogTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="prism-catalog-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.env = os.environ.copy()
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        for key in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
            self.env.pop(key, None)

    def cli(self, wrapper, *args, env=None):
        return subprocess.run(["/bin/bash", str(wrapper), *map(str, args)],
                              cwd=self.root, env=self.env if env is None else env,
                              capture_output=True, text=True, timeout=30)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_flat_output_remains_compatible_and_explicit_none_matches(self):
        old = self.cli(PAPER, "--list-templates")
        explicit = self.cli(PAPER, "--list-templates", "--group-by", "none")
        through_wrapper = self.cli(CATALOG, "--group-by", "none")
        for result in (old, explicit, through_wrapper):
            self.assert_success(result)
            self.assertEqual(result.stdout, old.stdout)
        lines = old.stdout.splitlines()
        self.assertEqual([line.split(":", 1)[0] for line in lines], list(templates.TEMPLATES))
        for alias, record in templates.TEMPLATES.items():
            line = next(line for line in lines if line.startswith(alias + ":"))
            self.assertIn("ID: " + record["id"], line)
            self.assertIn("type: " + record["kind"], line)
            self.assertIn("publisher: " + (record["publisher"] or "Prism"), line)

    def test_default_wrapper_groups_every_template_once_in_stable_order(self):
        result = self.cli(CATALOG)
        explicit = self.cli(PAPER, "--list-templates", "--group-by", "publisher")
        self.assert_success(result)
        self.assert_success(explicit)
        self.assertEqual(result.stdout, explicit.stdout)
        groups = {}
        current = None
        blocks = {}
        active_alias = None
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            if not line[0].isspace():
                current = line.strip()
                self.assertNotIn(current, groups)
                groups[current] = []
                active_alias = None
            else:
                match = re.match(r"^\s{2}([a-z][a-z0-9-]*):", line)
                if match:
                    alias = match.group(1)
                    self.assertIsNotNone(current)
                    self.assertNotIn(alias, blocks)
                    groups[current].append(alias)
                    blocks[alias] = line
                    active_alias = alias
                elif active_alias:
                    blocks[active_alias] += "\n" + line
        self.assertEqual(set(blocks), set(templates.TEMPLATES))
        expected_groups = {record["publisher"] for record in templates.TEMPLATES.values()
                           if record["publisher"]}
        expected_order = ["Prism / 通用", *sorted(expected_groups, key=str.casefold)]
        self.assertEqual(list(groups), expected_order)
        for label, aliases in groups.items():
            expected = sorted(aliases,
                              key=lambda alias: (templates.TEMPLATES[alias]["venue"].casefold(), alias))
            self.assertEqual(aliases, expected)
            for alias in aliases:
                record = templates.TEMPLATES[alias]
                self.assertEqual(label, record["publisher"] or "Prism / 通用")
                self.assertIn(record["venue"], blocks[alias])
                self.assertIn(record["id"], blocks[alias])
                if record.get("article_types"):
                    self.assertIn("--article-type:", blocks[alias])
                    self.assertIn("default: " + record["article_type"], blocks[alias])
                    for kind in record["article_types"]:
                        self.assertIn(kind, blocks[alias])
                else:
                    self.assertNotIn("--article-type", blocks[alias])
                    self.assertIn(record["description"], blocks[alias])

    def test_query_is_offline_and_needs_neither_tex_nor_project_metadata(self):
        tools = self.root / "only Python and shell utilities"
        tools.mkdir()
        for name, path in (("python3", sys.executable), ("dirname", shutil.which("dirname")),
                           ("bash", "/bin/bash")):
            self.assertIsNotNone(path)
            (tools / name).symlink_to(path)
        env = dict(self.env, PATH=str(tools))
        # A malformed current-directory project cannot influence the catalog.
        marker = self.root / templates.METADATA_NAME
        marker.write_bytes(b"not valid json; synthetic local material")
        before = marker.read_bytes()
        for wrapper, args in ((CATALOG, ()), (CATALOG, ("--version",)),
                              (CATALOG, ("--help",)), (PAPER, ("--list-templates",))):
            with self.subTest(wrapper=wrapper.name, args=args):
                result = self.cli(wrapper, *args, env=env)
                self.assert_success(result)
                self.assertEqual(marker.read_bytes(), before)
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network")) as fetch:
            grouped = templates.format_template_catalog("publisher")
            self.assertIn("angew:", grouped)
        fetch.assert_not_called()

    def test_invalid_group_combinations_are_rejected_without_directory_changes(self):
        target = self.root / "existing manuscript"
        target.mkdir()
        marker = target / "local.txt"
        marker.write_bytes(b"synthetic local author material")
        before = marker.read_bytes()
        for args in (("--init", target, "--force", "--group-by", "none"),
                     ("--init", target, "--force", "--group-by", "publisher"),
                     (target, "--group-by", "none"),
                     ("--check-deps", "--group-by", "publisher"),
                     ("--list-templates", "--group-by", "unknown"),
                     ("--list-templates", "--init", target, "--force", "--group-by", "publisher")):
            with self.subTest(args=args):
                result = self.cli(PAPER, *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(marker.read_bytes(), before)
                self.assertEqual(list(target.iterdir()), [marker])
                self.assertEqual(list(self.root.glob(target.name + ".backup*")), [])
        missing = self.root / "not created" / "manuscript"
        failed = self.cli(PAPER, "--init", missing, "--group-by", "none")
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse(missing.parent.exists())


if __name__ == "__main__":
    unittest.main()
