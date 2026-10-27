from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install-paper-skill.py"
SPEC = importlib.util.spec_from_file_location("prism_skill_install", SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class PaperSkillInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "Prism 中文 ' repository"
        self.repository(self.repo)
        self.skills = self.root / "user" / "skills"
        home = mock.patch.object(Path, "home", return_value=self.root / "home")
        home.start()
        self.addCleanup(home.stop)
        environment = mock.patch.dict(os.environ, {"CODEX_HOME": ""})
        environment.start()
        self.addCleanup(environment.stop)

    def repository(self, root, message="fixture wrapper"):
        for name in ("skills/paper-latex/SKILL.md", "scripts/lib/prism_latex/templates.py"):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic fixture\n")
        wrapper = root / "scripts/latex-paper.sh"
        wrapper.write_text("#!/bin/sh\nprintf '%s\\n' '" + message + "'\n")
        wrapper.chmod(0o755)

    def test_new_install_routes_to_complete_repository_without_copying_assets(self):
        target, backup = installer.install(self.repo, self.skills)
        self.assertIsNone(backup)
        self.assertEqual({p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()},
                         {"SKILL.md", "agents/openai.yaml", installer.MARKER})
        marker = json.loads((target / installer.MARKER).read_text())
        self.assertEqual(marker["repository"], str(self.repo))
        for name, digest in marker["files_sha256"].items():
            self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(), digest)
        self.assertFalse((target / "scripts").exists())
        self.assertFalse((target / "assets").exists())

    def test_router_shell_quoting_and_project_override(self):
        repo = self.root / "Prism 中文 ' $(touch injected-file)"
        self.repository(repo)
        target, _ = installer.install(repo, self.skills)
        text = (target / "SKILL.md").read_text()
        command = re.search(r"```bash\n(.*?)\n```", text, re.S).group(1)
        environment = os.environ.copy()
        environment.pop("PRISM_PROJECT_DIR", None)
        run = subprocess.run(["/bin/sh", "-c", command], cwd=self.root, env=environment,
                             text=True, capture_output=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip(), "fixture wrapper")
        self.assertFalse((self.root / "injected-file").exists())
        override = self.root / "override repository"
        self.repository(override, "override wrapper")
        environment["PRISM_PROJECT_DIR"] = str(override)
        run = subprocess.run(["/bin/sh", "-c", command], env=environment, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip(), "override wrapper")

    def test_repeated_install_is_noop_and_moved_checkout_updates_with_backup(self):
        target, _ = installer.install(self.repo, self.skills)
        before = installer.inventory(target)
        self.assertEqual(installer.install(self.repo, self.skills), (target, None))
        self.assertEqual(installer.inventory(target), before)
        moved = self.root / "moved Prism"
        self.repo.rename(moved)
        target, backup = installer.install(moved, self.skills)
        self.assertIsNotNone(backup)
        self.assertNotIn(self.skills, backup.parents)
        self.assertEqual(installer.inventory(backup), before)
        self.assertEqual(json.loads((target / installer.MARKER).read_text())["repository"], str(moved))

    def test_conflicting_skill_requires_force_and_backup_preserves_all_files(self):
        old = self.skills / "paper-latex"
        (old / "assets").mkdir(parents=True)
        (old / "SKILL.md").write_text("unrelated skill\n")
        (old / "assets" / "local.txt").write_text("local fixture content\n")
        before = installer.inventory(old)
        with self.assertRaisesRegex(installer.InstallError, "--force"):
            installer.install(self.repo, self.skills)
        self.assertEqual(installer.inventory(old), before)
        target, backup = installer.install(self.repo, self.skills, force=True)
        self.assertEqual(installer.inventory(backup), before)
        self.assertEqual((backup / "assets/local.txt").read_text(), "local fixture content\n")
        self.assertFalse((target / "assets").exists())

    def test_edited_managed_entry_requires_force(self):
        target, _ = installer.install(self.repo, self.skills)
        with (target / "SKILL.md").open("a") as handle:
            handle.write("user adjustment\n")
        with self.assertRaisesRegex(installer.InstallError, "edited"):
            installer.install(self.repo, self.skills)

    def test_non_object_marker_is_a_protected_conflict(self):
        for index, value in enumerate(([], None, 1, "text")):
            with self.subTest(value=value):
                skills = self.root / f"invalid-marker-{index}" / "skills"
                target, _ = installer.install(self.repo, skills)
                (target / installer.MARKER).write_text(json.dumps(value))
                before = installer.inventory(target)
                with self.assertRaisesRegex(installer.InstallError, "--force"):
                    installer.install(self.repo, skills)
                self.assertEqual(installer.inventory(target), before)

    def test_earlier_prism_router_is_recognized_and_fully_backed_up(self):
        target = self.skills / "paper-latex"
        (target / "scripts").mkdir(parents=True)
        (target / "scripts" / "old.py").write_text("legacy fixture\n")
        (target / "SKILL.md").write_text(
            "---\nname: paper-latex\n---\n"
            "Use the current Prism repository as the source of truth for manuscript workflows.\n"
            f"Set PRISM_PROJECT_DIR when moved; otherwise use `{self.repo}`.\n"
            "Do not fall back to this skill directory's older scripts or assets.\n")
        _, backup = installer.install(self.repo, self.skills)
        self.assertEqual((backup / "scripts/old.py").read_text(), "legacy fixture\n")

    def test_default_location_prefers_existing_and_refuses_duplicate_entries(self):
        home = self.root / "home"
        with mock.patch.object(Path, "home", return_value=home), mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(installer.choose_skills_dir(None), home / ".agents/skills")
            old = home / ".codex/skills/paper-latex"
            old.mkdir(parents=True)
            self.assertEqual(installer.choose_skills_dir(None), old.parent)
            (home / ".agents/skills/paper-latex").mkdir(parents=True)
            with self.assertRaisesRegex(installer.InstallError, "Multiple"):
                installer.choose_skills_dir(None)
            with self.assertRaisesRegex(installer.InstallError, "duplicate"):
                installer.choose_skills_dir(self.skills)
            self.assertEqual(installer.choose_skills_dir(old.parent), old.parent)

    def test_explicit_new_location_cannot_create_duplicate_in_known_directories(self):
        home = Path.home()
        original = home / ".codex/skills"
        target, _ = installer.install(self.repo, original)
        before = installer.inventory(target)
        other = home / ".agents/skills"
        with self.assertRaisesRegex(installer.InstallError, "duplicate"):
            installer.install(self.repo, other)
        self.assertEqual(installer.inventory(target), before)
        self.assertFalse((other / "paper-latex").exists())

    def test_custom_codex_home_is_detected(self):
        home = self.root / "home"
        custom = self.root / "codex"
        (custom / "skills/paper-latex").mkdir(parents=True)
        with mock.patch.object(Path, "home", return_value=home), mock.patch.dict(os.environ, {"CODEX_HOME": str(custom)}, clear=True):
            self.assertEqual(installer.choose_skills_dir(None), custom / "skills")

    def test_symlinks_and_incomplete_or_overlapping_repository_are_rejected(self):
        self.skills.mkdir(parents=True)
        target = self.skills / "paper-latex"
        target.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallError, "Symbolic"):
            installer.install(self.repo, self.skills, force=True)
        target.unlink()
        target.mkdir()
        (target / "linked").symlink_to(self.repo / "skills/paper-latex/SKILL.md")
        with self.assertRaisesRegex(installer.InstallError, "symbolic"):
            installer.install(self.repo, self.skills, force=True)
        with self.assertRaisesRegex(installer.InstallError, "complete"):
            installer.install(self.root / "missing", self.skills)
        with self.assertRaisesRegex(installer.InstallError, "outside"):
            installer.install(self.repo, self.repo / "skills", force=True)

    def test_publication_failure_restores_original_skill(self):
        target, _ = installer.install(self.repo, self.skills)
        before = installer.inventory(target)
        moved = self.root / "moved Prism"
        self.repo.rename(moved)
        with mock.patch.object(installer.os, "replace", side_effect=OSError("synthetic publication failure")):
            with self.assertRaises(OSError):
                installer.install(moved, self.skills)
        self.assertEqual(installer.inventory(target), before)
        self.assertFalse(list(self.skills.parent.glob(".prism-paper-stage-*")))

    def test_concurrent_edit_stops_before_backup(self):
        target, _ = installer.install(self.repo, self.skills)
        moved = self.root / "moved Prism"
        self.repo.rename(moved)
        original = installer.generated_files

        def edit_during_preparation(repository):
            with (target / "SKILL.md").open("a") as handle:
                handle.write("concurrent fixture edit\n")
            return original(repository)

        with mock.patch.object(installer, "generated_files", side_effect=edit_during_preparation):
            with self.assertRaisesRegex(installer.InstallError, "changed during preparation"):
                installer.install(moved, self.skills)
        self.assertTrue((target / "SKILL.md").read_text().endswith("concurrent fixture edit\n"))
        self.assertFalse((self.skills.parent / "prism-skill-backups").exists())

    def test_post_publication_verification_failure_restores_old_and_retains_failed_files(self):
        target, _ = installer.install(self.repo, self.skills)
        before = installer.inventory(target)
        moved = self.root / "moved Prism"
        self.repo.rename(moved)
        replace = installer.os.replace

        def corrupt_after_publish(source, destination):
            replace(source, destination)
            (destination / "SKILL.md").write_text("synthetic corrupted publication\n")

        with mock.patch.object(installer.os, "replace", side_effect=corrupt_after_publish):
            with self.assertRaisesRegex(installer.InstallError, "previous state was restored"):
                installer.install(moved, self.skills)
        self.assertEqual(installer.inventory(target), before)
        retained = list((self.skills.parent / "prism-skill-backups").glob("*/failed-installation/SKILL.md"))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].read_text(), "synthetic corrupted publication\n")


if __name__ == "__main__":
    unittest.main()
