from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export-public-code.py"
SPEC = importlib.util.spec_from_file_location("prism_public_export", SCRIPT)
EXPORT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPORT
SPEC.loader.exec_module(EXPORT)


class PublicExportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / "source"
        self.source.mkdir()
        self.write("README.md", "# Portable workflow\n")
        self.write("LICENSE", "MIT attribution retained.\n")
        self.write("projects/.gitkeep", "")
        self.output = self.root / "public snapshot"
        self.manifest = self.root / "inventory.json"

    def write(self, relative, content):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_cli(self, *options):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "--source", str(self.source), *map(str, options)],
                              text=True, capture_output=True, check=False, timeout=20)

    def test_export_uses_allowlist_without_git_and_preserves_text_and_execution(self):
        self.write("VERSION", "1.0.0\n")
        runner = self.write("scripts/run.sh", "#!/bin/sh\nexit 0\n")
        runner.chmod(0o755)
        self.write("skills/paper/assets/references.bib", "@misc{sample, title={Demonstration}}\n")
        self.write("docs/中文 guide.md", "# 使用指南\n")
        self.write("tests/fixtures/review.md", "Journal: Example Journal\nReview ID: MS-EXAMPLE\n")
        self.write("projects/Notes/private.md", "local research\n")
        self.write("archives/snapshot/README.md", "historical material\n")
        self.write("references.bib", "private collection\n")
        self.write("latex-templates/template.tex", "retired material\n")
        self.write(".git/config", "remote and identity\n")
        self.write(".env", "local configuration\n")
        result = self.run_cli("--out", self.output, "--manifest", self.manifest)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = {
            "README.md", "LICENSE", "VERSION", "projects/.gitkeep", "scripts/run.sh",
            "skills/paper/assets/references.bib", "docs/中文 guide.md", "tests/fixtures/review.md",
        }
        self.assertEqual({path.relative_to(self.output).as_posix() for path in self.output.rglob("*") if path.is_file()}, expected)
        self.assertEqual((self.output / "scripts/run.sh").stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.output / "docs/中文 guide.md").read_text(), "# 使用指南\n")
        data = json.loads(self.manifest.read_text())
        self.assertEqual(data["file_count"], len(expected))
        self.assertEqual({entry["path"] for entry in data["files"]}, expected)
        self.assertNotIn(str(self.source), self.manifest.read_text())
        self.assertFalse((self.output / "inventory.json").exists())
        self.assertFalse(list(self.root.glob(".prism-export-*")))

    def test_audit_checks_untracked_maintained_files_and_never_prints_values(self):
        examples = {
            "home": "/" + "Users" + "/" + "private-person" + "/" + "draft.tex",
            "linux_home": "/" + "home" + "/" + "private-person" + "/" + "draft.tex",
            "unicode_home": "/" + "Users" + "/" + "研究者" + "/" + "draft.tex",
            "windows_home": "C:" + chr(92) + "Users" + chr(92) + "private-person" + chr(92) + "draft.tex",
            "email": "researcher" + chr(64) + "institution.edu",
            "github": "gh" + "p_" + "a" * 36,
            "aws": "AK" + "IA" + "A" * 16,
            "openai": "sk" + "-" + "a" * 40,
            "private_key": "-----BEGIN " + "RSA " + "PRIVATE " + "KEY-----",
        }
        for name, private_value in examples.items():
            with self.subTest(name=name):
                candidate = self.write("docs/new.md", "Private value: " + private_value + "\n")
                result = self.run_cli("--check")
                self.assertEqual(result.returncode, 1)
                self.assertIn("docs/new.md:", result.stderr)
                self.assertNotIn(private_value, result.stdout + result.stderr)
                candidate.unlink()
        self.assertFalse(self.output.exists())

    def test_example_contacts_regex_source_and_synthetic_fixture_are_allowed(self):
        self.write("skills/paper/main.tex", "Contact: author@example.org\n")
        self.write("tests/pattern.py", "PATTERN = r'[A-Z0-9._%+-]+@([A-Z0-9.-]+\\.[A-Z]{2,})'\n")
        self.write("tests/fixtures/review.md", "Journal: Example Journal\nReview ID: MS-EXAMPLE\nConfidential Comments to Editor\nSynthetic fixture only.\n")
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Audit passed", result.stdout)
        self.assertEqual(sorted(self.root.iterdir()), [self.source])

    def test_symlinks_are_blocked_without_traversing_external_or_excluded_roots(self):
        outside = self.root / "private"
        outside.mkdir()
        (outside / "document.md").write_text("private content\n")
        link = self.source / "docs"
        link.symlink_to(outside, target_is_directory=True)
        result = self.run_cli("--out", self.output)
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs: symlink", result.stderr)
        self.assertNotIn("private content", result.stderr)
        self.assertFalse(self.output.exists())
        link.unlink()
        (self.source / "External").symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.run_cli("--check").returncode, 0)
        self.write("docs/safe.md", "safe\n")
        (self.source / "docs" / "linked.md").symlink_to(outside / "document.md")
        self.assertEqual(self.run_cli("--check").returncode, 1)

    def test_caches_and_compiler_outputs_are_excluded_even_if_force_tracked(self):
        self.write("scripts/__pycache__/cached.pyc", "cached\n")
        self.write("skills/paper/main.aux", "intermediate\n")
        self.write("skills/paper/main.synctex.gz", "intermediate\n")
        self.write("skills/paper/.DS_Store", "desktop metadata\n")
        self.write("scripts/run.py", "print('safe')\n")
        # The exporter never consults an index, including a force-tracked one.
        self.write(".git/index", "tracked cache names would not change the allowlist\n")
        result = self.run_cli("--out", self.output, "--manifest", self.manifest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.output / "scripts/__pycache__").exists())
        self.assertFalse((self.output / "skills/paper/main.aux").exists())
        counts = json.loads(self.manifest.read_text())["exclusions"]
        self.assertEqual(counts["generated-directories"], 1)
        self.assertEqual(counts["generated-files"], 3)

    def test_nested_repository_binary_and_unrecognized_files_are_blocked(self):
        for relative, data in [
            ("skills/example/.git/config", b"metadata"),
            ("docs/preview.pdf", b"%PDF-1.7"),
            ("docs/payload.md", b"hello\0binary"),
            ("docs/raw.txt", bytes([255, 254])),
        ]:
            with self.subTest(relative=relative):
                path = self.source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                self.assertEqual(self.run_cli("--check").returncode, 1)
                path.unlink()
                while path.parent != self.source and not any(path.parent.iterdir()):
                    path = path.parent
                    path.rmdir()

    def test_source_change_aborts_without_partial_snapshot_or_manifest(self):
        original_read = EXPORT._read_regular
        calls = 0

        def changing_read(source, relative):
            nonlocal calls
            result = original_read(source, relative)
            calls += 1
            if calls == 3:
                self.write("README.md", "changed after initial inventory\n")
            return result

        with mock.patch.object(EXPORT, "_read_regular", side_effect=changing_read):
            with self.assertRaisesRegex(EXPORT.ExportError, "source-changed|Source changed"):
                EXPORT.export(self.source, self.output, self.manifest)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())
        self.assertFalse(list(self.root.glob(".prism-export-*")))

    def test_new_source_file_during_copy_aborts(self):
        original_read = EXPORT._read_regular
        calls = 0

        def adding_read(source, relative):
            nonlocal calls
            result = original_read(source, relative)
            calls += 1
            if calls == 4:
                self.write("docs/added.md", "new source\n")
            return result

        with mock.patch.object(EXPORT, "_read_regular", side_effect=adding_read):
            with self.assertRaisesRegex(EXPORT.ExportError, "Source changed"):
                EXPORT.export(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_outputs_and_source_boundaries_are_preserved(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("preserve\n")
        self.assertEqual(self.run_cli("--out", self.output).returncode, 1)
        self.assertEqual(sentinel.read_text(), "preserve\n")
        (self.source / "docs").mkdir()
        self.assertEqual(self.run_cli("--out", self.source / "docs" / "snapshot").returncode, 1)
        self.assertEqual(self.run_cli("--out", self.root / "new", "--manifest", self.source / "docs" / "manifest.json").returncode, 1)
        self.manifest.write_text("preserve manifest\n")
        self.assertEqual(self.run_cli("--out", self.root / "new", "--manifest", self.manifest).returncode, 1)
        self.assertEqual(self.manifest.read_text(), "preserve manifest\n")
        (self.source / ".git").mkdir()
        self.assertEqual(self.run_cli("--out", self.source / ".git" / "snapshot").returncode, 1)
        self.assertEqual(self.run_cli("--out", self.root / "new", "--manifest", self.source / ".git" / "manifest.json").returncode, 1)

    def test_concurrent_output_collision_rolls_back_local_manifest(self):
        def collide(staged, destination):
            destination.mkdir()
            (destination / "keep.txt").write_text("competing output\n")
            raise EXPORT.ExportError("Output already exists; choose a new directory.")

        with mock.patch.object(EXPORT, "_publish_directory", side_effect=collide):
            with self.assertRaisesRegex(EXPORT.ExportError, "already exists"):
                EXPORT.export(self.source, self.output, self.manifest)
        self.assertEqual((self.output / "keep.txt").read_text(), "competing output\n")
        self.assertFalse(self.manifest.exists())

    def test_atomic_publish_refuses_an_existing_empty_directory(self):
        staged = self.root / "staged"
        staged.mkdir()
        (staged / "README.md").write_text("staged source\n")
        self.output.mkdir()
        with self.assertRaisesRegex(EXPORT.ExportError, "already exists"):
            EXPORT._publish_directory(staged, self.output)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertTrue((staged / "README.md").is_file())

    def test_export_can_live_under_local_archive_without_traversing_it(self):
        archives = self.source / "archives"
        archives.mkdir()
        output = archives / "public"
        result = self.run_cli("--out", output, "--manifest", archives / "manifest.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((output / "archives").exists())


if __name__ == "__main__":
    unittest.main()
