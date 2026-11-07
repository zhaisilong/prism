from __future__ import annotations

import importlib.util
import hashlib
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
        self.reviewed = {EXPORT.PUBLIC_FILE_LIST}
        self.write("README.md", "# Portable workflow\n")
        self.write("LICENSE", "MIT attribution retained.\n")
        self.write("projects/.gitkeep", "")
        self.output = self.root / "public snapshot"
        self.manifest = self.root / "inventory.json"

    def approve(self, *paths):
        self.reviewed.update(paths)
        listing = self.source / EXPORT.PUBLIC_FILE_LIST
        listing.parent.mkdir(parents=True, exist_ok=True)
        listing.write_text("\n".join(sorted(self.reviewed)) + "\n", encoding="utf-8")

    def write(self, relative, content, *, reviewed=True):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        parts = Path(relative).parts
        generated = (any(part in EXPORT.CACHE_DIRS | EXPORT.METADATA_NAMES for part in parts)
                     or path.suffix in EXPORT.GENERATED_SUFFIXES or path.name == ".DS_Store"
                     or path.name.endswith((".run.xml", ".synctex.gz")))
        if (reviewed and not generated and (relative in EXPORT.ROOT_FILES
                or relative == "projects/.gitkeep" or parts[0] in EXPORT.SOURCE_DIRS)):
            self.approve(relative)
        return path

    def run_cli(self, *options):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "--source", str(self.source), *map(str, options)],
                              text=True, capture_output=True, check=False, timeout=20)

    def test_export_uses_allowlist_without_git_and_preserves_text_and_execution(self):
        self.write(".gitattributes", "skills/paper-latex/assets/upstream/** -text -whitespace\n")
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
            ".gitattributes", "README.md", "LICENSE", "VERSION", "projects/.gitkeep", "scripts/run.sh", EXPORT.PUBLIC_FILE_LIST,
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

    def test_directory_swaps_during_enumeration_never_follow_external_links(self):
        self.write("docs/guide.md", "Public synthetic guide.\n")
        outside = self.root / "external"
        outside.mkdir()
        (outside / "docs").mkdir()
        private_name = "SYNTHETIC-PRIVATE-RESEARCH-TITLE.txt"
        (outside / private_name).write_text("Synthetic private text.\n")
        (outside / "docs" / private_name).write_text("Synthetic private text.\n")
        identity = lambda info: (info.st_dev, info.st_ino)
        outside_identities = {identity(outside.stat()), identity((outside / "docs").stat())}
        original_listdir = os.listdir

        for victim in (self.source, self.source / "docs"):
            with self.subTest(boundary=victim.name):
                victim_identity = identity(victim.stat())
                saved = self.root / "moved-directory"
                swapped = False
                enumerated_outside = False

                def swapping_listdir(path):
                    nonlocal swapped, enumerated_outside
                    info = os.fstat(path) if isinstance(path, int) else os.stat(path)
                    if identity(info) == victim_identity and not swapped:
                        victim.rename(saved)
                        victim.symlink_to(outside, target_is_directory=True)
                        swapped = True
                    enumerated = os.fstat(path) if isinstance(path, int) else os.stat(path)
                    enumerated_outside |= identity(enumerated) in outside_identities
                    return original_listdir(path)

                try:
                    with mock.patch.object(EXPORT.os, "listdir", side_effect=swapping_listdir):
                        with self.assertRaises(EXPORT.ExportError) as caught:
                            EXPORT.export(self.source, self.output, self.manifest)
                    self.assertTrue(swapped)
                    self.assertFalse(enumerated_outside)
                    self.assertNotIn(private_name, str(caught.exception))
                    self.assertFalse(self.output.exists())
                    self.assertFalse(self.manifest.exists())
                finally:
                    if swapped:
                        victim.unlink()
                        saved.rename(victim)

    def test_project_swap_before_placeholder_lookup_never_stats_external_content(self):
        outside = self.root / "external"
        outside.mkdir()
        outside_placeholder = outside / ".gitkeep"
        outside_placeholder.write_text("Synthetic private text.\n")
        victim = self.source / "projects"
        saved = self.root / "moved-projects"
        identity = lambda info: (info.st_dev, info.st_ino)
        victim_identity = identity(victim.stat())
        private_identity = identity(outside_placeholder.stat())
        original_stat = os.stat
        swapped = False
        inspected_outside = False

        def swapping_stat(path, *args, **kwargs):
            nonlocal swapped, inspected_outside
            parent_fd = kwargs.get("dir_fd")
            placeholder_lookup = (
                path == ".gitkeep" and parent_fd is not None
                and identity(os.fstat(parent_fd)) == victim_identity
            ) or (parent_fd is None and Path(path) == victim / ".gitkeep")
            if placeholder_lookup and not swapped:
                victim.rename(saved)
                victim.symlink_to(outside, target_is_directory=True)
                swapped = True
            result = original_stat(path, *args, **kwargs)
            if placeholder_lookup:
                inspected_outside |= identity(result) == private_identity
            return result

        try:
            with mock.patch.object(EXPORT.os, "stat", side_effect=swapping_stat):
                with self.assertRaises(EXPORT.ExportError) as caught:
                    EXPORT.export(self.source, self.output, self.manifest)
            self.assertTrue(swapped)
            self.assertFalse(inspected_outside)
            self.assertNotIn("Synthetic private text", str(caught.exception))
            self.assertFalse(self.output.exists())
            self.assertFalse(self.manifest.exists())
        finally:
            if swapped:
                victim.unlink()
                saved.rename(victim)

    def test_reviewed_upstream_notices_keep_attribution_only_at_exact_paths(self):
        for relative in EXPORT.UPSTREAM_NOTICE_SHA256:
            target = self.source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
            self.approve(relative)
        result = self.run_cli("--out", self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        for relative in EXPORT.UPSTREAM_NOTICE_SHA256:
            self.assertEqual((self.output / relative).read_bytes(), (ROOT / relative).read_bytes())
        unrelated = self.source / "docs/copied-notice.txt"
        unrelated.parent.mkdir(exist_ok=True)
        unrelated.write_bytes((ROOT / next(iter(EXPORT.UPSTREAM_NOTICE_SHA256))).read_bytes())
        self.approve("docs/copied-notice.txt")
        rejected = self.run_cli("--check")
        self.assertEqual(rejected.returncode, 1)
        self.assertIn("docs/copied-notice.txt: non-example-email", rejected.stderr)

    def test_changed_upstream_notice_cannot_hide_personal_data(self):
        relative = next(iter(EXPORT.UPSTREAM_NOTICE_SHA256))
        original = (ROOT / relative).read_bytes()
        target = self.source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        private = "private-person" + chr(64) + "private-domain.invalid"
        target.write_bytes(original + ("\n" + private).encode())
        self.approve(relative)
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("upstream-notice-changed", result.stderr)
        self.assertIn("non-example-email", result.stderr)
        self.assertNotIn(private, result.stdout + result.stderr)
        target.write_bytes(original + b"\n")
        self.assertEqual(self.run_cli("--check").returncode, 1)

    def test_attribution_exception_never_disables_credentials_or_path_checks(self):
        relative = next(iter(EXPORT.UPSTREAM_NOTICE_SHA256))
        fixtures = {
            "github-token": "gh" + "p_" + "A" * 36,
            "absolute-home-path": "/" + "Users" + "/" + "private-person" + "/draft.tex",
        }
        for rule, private in fixtures.items():
            with self.subTest(rule=rule):
                target = self.source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                content = ("Copyright contact: " + private + "\n").encode()
                target.write_bytes(content)
                self.approve(relative)
                approved = {relative: hashlib.sha256(content).hexdigest()}
                with mock.patch.object(EXPORT, "UPSTREAM_NOTICE_SHA256", approved):
                    with self.assertRaisesRegex(EXPORT.ExportError, rule) as caught:
                        EXPORT.inventory(self.source)
                self.assertNotIn(private, str(caught.exception))

    def test_caches_and_compiler_outputs_are_excluded_even_if_force_tracked(self):
        self.write("scripts/__pycache__/cached.pyc", "cached\n")
        self.write("skills/paper/main.aux", "intermediate\n")
        self.write("skills/paper/main.spl", "intermediate\n")
        self.write("skills/paper/main.synctex.gz", "intermediate\n")
        self.write("skills/paper/.DS_Store", "desktop metadata\n")
        self.write("scripts/run.py", "print('safe')\n")
        # The exporter never consults an index, including a force-tracked one.
        self.write(".git/index", "tracked cache names would not change the allowlist\n")
        result = self.run_cli("--out", self.output, "--manifest", self.manifest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.output / "scripts/__pycache__").exists())
        self.assertFalse((self.output / "skills/paper/main.aux").exists())
        self.assertFalse((self.output / "skills/paper/main.spl").exists())
        counts = json.loads(self.manifest.read_text())["exclusions"]
        self.assertEqual(counts["generated-directories"], 1)
        self.assertEqual(counts["generated-files"], 4)

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
            if calls == 4:
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
                self.write("docs/added.md", "new source\n", reviewed=False)
            return result

        with mock.patch.object(EXPORT, "_read_regular", side_effect=adding_read):
            with self.assertRaisesRegex(EXPORT.ExportError, "source-changed|Source changed|unreviewed-public-path"):
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

    def test_exact_file_list_is_required_and_must_include_itself(self):
        listing = self.source / EXPORT.PUBLIC_FILE_LIST
        listing.unlink()
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsafe-or-unreadable-file-list", result.stderr)
        listing.write_text("README.md\nLICENSE\nprojects/.gitkeep\n")
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("file-list-must-include-itself", result.stderr)

    def test_unreviewed_research_text_files_are_rejected_without_scanning_contents(self):
        for relative, content in {
            "docs/report.json": '{"values":[17,23],"status":"synthetic"}\n',
            "tests/manuscript.tex": "Synthetic unpublished paragraph.\n",
            "docs/references.bib": "@misc{synthetic, title={Private example}}\n",
            "docs/table.tsv": "item\tvalue\nA\t17\n",
        }.items():
            with self.subTest(relative=relative):
                path = self.write(relative, content, reviewed=False)
                result = self.run_cli("--out", self.output)
                self.assertEqual(result.returncode, 1)
                self.assertIn(relative + ": unreviewed-public-path", result.stderr)
                self.assertNotIn(content.strip(), result.stdout + result.stderr)
                self.assertFalse(self.output.exists())
                path.unlink()

    def test_approved_template_metadata_and_demo_sources_remain_exportable(self):
        self.write("skills/paper/assets/demo/main.tex", "\\documentclass{article}\n")
        self.write("skills/paper/assets/demo/references.bib", "@misc{demo, title={Example}}\n")
        self.write("skills/paper/assets/upstream/manifest.json", '{"version":"1","source":"example"}\n')
        result = self.run_cli("--out", self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.output / "skills/paper/assets/upstream/manifest.json").read_text())["version"], "1")

    def test_invalid_public_paths_and_duplicates_do_not_echo_rows(self):
        invalid = [
            "/private/hidden/source.tex", "../outside.md", "scripts/../outside.md",
            "docs//file.md", "docs/./file.md", "docs/*.tex", "docs/file?.md",
            "docs/[ab].md", "docs/{one,two}.md", "C:\\hidden\\source.tex", "docs/trailing.md ",
            "scripts", "archives/private.md", "projects/private.tex", "unknown.txt",
        ]
        listing = self.source / EXPORT.PUBLIC_FILE_LIST
        original = listing.read_text()
        for row in invalid:
            with self.subTest(row=row):
                listing.write_text(original + row + "\n")
                result = self.run_cli("--check")
                self.assertEqual(result.returncode, 1)
                self.assertIn("invalid-public-file-path", result.stderr)
                self.assertRegex(result.stderr, r"^scripts/public-export-files\.txt:\d+: invalid-public-file-path\n$")
        listing.write_text(original + "README.md\n")
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate-public-file-path", result.stderr)

    def test_missing_and_directory_entries_are_rejected(self):
        self.approve("docs/missing.md", "docs/directory")
        (self.source / "docs/directory").mkdir(parents=True)
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/missing.md: reviewed-file-missing", result.stderr)
        self.assertIn("docs/directory: reviewed-file-missing", result.stderr)

    def test_protected_copy_renaming_and_hardlinks_are_blocked_at_approved_paths(self):
        secret = self.root / "private-authored.tex"
        content = "Synthetic protected manuscript: sample Z, value 4729.\n"
        secret.write_text(content)
        candidate = self.write("docs/approved.txt", "Public explanation.\n")
        for method in ("copy", "hardlink"):
            with self.subTest(method=method):
                candidate.unlink()
                if method == "copy":
                    candidate.write_bytes(secret.read_bytes())
                else:
                    os.link(secret, candidate)
                result = self.run_cli("--out", self.output, "--manifest", self.manifest,
                                      "--protect-file", secret)
                self.assertEqual(result.returncode, 1)
                self.assertIn("docs/approved.txt: protected-content-match", result.stderr)
                self.assertNotIn(str(secret), result.stdout + result.stderr)
                self.assertNotIn(content.strip(), result.stdout + result.stderr)
                self.assertNotIn(hashlib.sha256(secret.read_bytes()).hexdigest(), result.stdout + result.stderr)
                self.assertFalse(self.output.exists())
                self.assertFalse(self.manifest.exists())

    def test_multiple_protected_files_are_supported_and_never_recorded(self):
        first = self.root / "private-one.tex"
        second = self.root / "private-two.bib"
        first.write_text("Synthetic private source one.\n")
        second.write_text("Synthetic private source two.\n")
        candidate = self.write("docs/approved.md", second.read_text())
        result = self.run_cli("--check", "--protect-file", first, "--protect-file", second)
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected-content-match", result.stderr)
        candidate.write_text("Public synthetic explanation.\n")
        result = self.run_cli("--out", self.output, "--manifest", self.manifest,
                              "--protect-file", first, "--protect-file", second)
        self.assertEqual(result.returncode, 0, result.stderr)
        public = self.manifest.read_text() + (self.output / EXPORT.PUBLIC_FILE_LIST).read_text() + result.stdout
        for protected in (first, second):
            self.assertNotIn(str(protected), public)
            self.assertNotIn(protected.name, public)
            self.assertNotIn(hashlib.sha256(protected.read_bytes()).hexdigest(), public)
        self.assertEqual({path.name for path in self.output.iterdir()}, {"README.md", "LICENSE", "projects", "scripts", "docs"})

    def test_protected_symlinks_directories_and_missing_files_have_private_errors(self):
        private = self.root / "private-dir"
        private.mkdir()
        original = private / "private-source.tex"
        original.write_text("Synthetic protected source.\n")
        linked_file = self.root / "private-link.tex"
        linked_file.symlink_to(original)
        linked_parent = self.root / "private-parent-link"
        linked_parent.symlink_to(private, target_is_directory=True)
        for protected in (linked_file, linked_parent / original.name, private, private / "absent.tex"):
            with self.subTest(protected=protected.name):
                result = self.run_cli("--check", "--protect-file", protected)
                self.assertEqual(result.returncode, 1)
                self.assertIn("protected-file-", result.stderr)
                self.assertNotIn(str(protected), result.stdout + result.stderr)
                self.assertNotIn(protected.name, result.stdout + result.stderr)

    def test_protected_file_changes_abort_audit_and_preserve_outputs(self):
        private = self.root / "private-source.tex"
        private.write_text("Synthetic protected original.\n")
        original = EXPORT._read_protected
        calls = 0

        def changing_protected(path):
            nonlocal calls
            result = original(path)
            calls += 1
            if calls == 1:
                private.write_text("Synthetic protected replacement.\n")
            return result

        with mock.patch.object(EXPORT, "_read_protected", side_effect=changing_protected):
            with self.assertRaisesRegex(EXPORT.ExportError, "protected-file-changed") as caught:
                EXPORT.inventory(self.source, [private])
        self.assertNotIn(str(private), str(caught.exception))
        self.assertFalse(self.output.exists())

    def test_protected_file_change_before_publication_rolls_back_manifest(self):
        private = self.root / "private-source.tex"
        private.write_text("Synthetic protected original.\n")
        original = EXPORT._verify_protected
        calls = 0

        def changing_verification(protected):
            nonlocal calls
            calls += 1
            if calls == 3:
                private.write_text("Synthetic protected changed before publication.\n")
            return original(protected)

        with mock.patch.object(EXPORT, "_verify_protected", side_effect=changing_verification):
            with self.assertRaisesRegex(EXPORT.ExportError, "protected-file-changed"):
                EXPORT.export(self.source, self.output, self.manifest, [private])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())
        self.assertFalse(list(self.root.glob(".prism-export-*")))

    def test_file_list_change_during_audit_cannot_expand_reviewed_paths(self):
        original = EXPORT._read_regular
        calls = 0

        def changing_listing(source, relative):
            nonlocal calls
            result = original(source, relative)
            calls += 1
            if calls == 1:
                self.write("docs/new.md", "Newly added unreviewed content.\n")
            return result

        with mock.patch.object(EXPORT, "_read_regular", side_effect=changing_listing):
            with self.assertRaisesRegex(EXPORT.ExportError, "source-changed"):
                EXPORT.inventory(self.source)

    def test_large_protected_files_are_hashed_without_public_text_size_limit(self):
        private = self.root / "private-payload.bin"
        private.write_bytes(b"synthetic" * (EXPORT.MAX_TEXT_BYTES // 9 + 1))
        self.assertGreater(private.stat().st_size, EXPORT.MAX_TEXT_BYTES)
        result = self.run_cli("--check", "--protect-file", private)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
