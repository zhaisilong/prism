from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_writer(skill: str):
    path = ROOT / f"skills/{skill}/scripts/build_script.py"
    name = "prism_build_script_" + skill.replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class BuildScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.writers = {
            skill: load_writer(skill)
            for skill in ("notes-latex", "reviewer-latex", "paper-latex")
        }

    def make_stub(self, skills_dir: Path, workflow: str, origin: str | None = None) -> None:
        entrypoint = skills_dir / workflow / "scripts" / f"{workflow.replace('-', '_')}.py"
        entrypoint.parent.mkdir(parents=True)
        arguments = "sys.argv[1:]" if origin is None else f"[{origin!r}, *sys.argv[1:]]"
        entrypoint.write_text(f"import json, sys\nprint(json.dumps({arguments}, ensure_ascii=False))\n", encoding="utf-8")

    def make_local_repo(self, repo: Path, workflow: str, origin: str = "local") -> None:
        self.make_stub(repo / "skills", workflow, origin)
        wrappers = {"notes-latex": "latex-note.sh", "reviewer-latex": "latex-review.sh", "paper-latex": "latex-paper.sh"}
        wrapper = repo / "scripts" / wrappers[workflow]
        wrapper.parent.mkdir(parents=True, exist_ok=True)
        wrapper.write_text(
            '#!/usr/bin/env bash\nset -Eeuo pipefail\n'
            'ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"\n'
            f'exec {shlex.quote(sys.executable)} "$ROOT_DIR/skills/{workflow}/scripts/{workflow.replace("-", "_")}.py" "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o755)

    def local_env(self, root: Path):
        env = os.environ.copy()
        for key in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
            env.pop(key, None)
        env["HOME"] = str(root / "empty home")
        env["CODEX_HOME"] = str(root / "empty codex")
        return env

    def test_generated_scripts_preserve_portable_paths_and_arguments(self):
        for workflow in self.writers:
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                project = root / "项目 with spaces"
                project.mkdir()
                input_path = project / ("main.tex" if workflow == "paper-latex" else "draft '一'.md")
                input_path.write_text("content", encoding="utf-8")
                output_path = project / "result 文件.pdf"
                options = ["--engine", "auto", "--title", 'A "quoted" title', "--strict"]
                script = self.writers[workflow].write_build_script(
                    workflow=workflow,
                    input_path=input_path,
                    output_path=output_path,
                    project_dir=project,
                    options=options,
                )
                self.assertEqual(script, (project / "prism-build.sh").resolve())
                self.assertTrue(os.access(script, os.X_OK))

                skills_dir = root / "installed skills"
                self.make_stub(skills_dir, workflow)
                env = os.environ.copy()
                env["PRISM_LATEX_SKILLS_DIR"] = str(skills_dir)
                result = subprocess.run(
                    [str(script)], capture_output=True, text=True, env=env, check=False
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                arguments = json.loads(result.stdout)
                expected_input = project if workflow == "paper-latex" else input_path
                self.assertEqual(Path(arguments[0]).resolve(), expected_input.resolve())
                self.assertEqual(arguments[1], "--out")
                self.assertEqual(Path(arguments[2]).resolve(), output_path.resolve())
                self.assertEqual(arguments[3:-1], options)
                self.assertEqual(arguments[-1], "--no-build-script")

    def test_conflict_is_preserved_unless_force_is_explicit(self):
        writer = self.writers["notes-latex"]
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            source = project / "note.md"
            output = project / "note.pdf"
            source.write_text("note", encoding="utf-8")
            script = project / "prism-build.sh"
            script.write_text("#!/bin/sh\necho user-owned\n", encoding="utf-8")

            result = writer.write_build_script(
                workflow="notes-latex",
                input_path=source,
                output_path=output,
                project_dir=project,
                options=["--engine", "auto"],
            )
            self.assertIsNone(result)
            self.assertIn("user-owned", script.read_text(encoding="utf-8"))

            result = writer.write_build_script(
                workflow="notes-latex",
                input_path=source,
                output_path=output,
                project_dir=project,
                options=["--engine", "auto"],
                force=True,
            )
            self.assertEqual(result, script.resolve())
            self.assertTrue(list(project.glob("prism-build.sh.backup-*")))
            self.assertIn("# prism-workflow: notes-latex", script.read_text(encoding="utf-8"))

    def test_matching_managed_script_is_refreshed_without_backup(self):
        writer = self.writers["paper-latex"]
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            source = project / "main.tex"
            source.write_text("content", encoding="utf-8")
            output = project / "main.pdf"
            for engine in ("auto", "lualatex"):
                writer.write_build_script(
                    workflow="paper-latex",
                    input_path=source,
                    output_path=output,
                    project_dir=project,
                    options=["--main", "main.tex", "--engine", engine],
                )
            self.assertFalse(list(project.glob("prism-build.sh.backup-*")))
            self.assertIn("lualatex", (project / "prism-build.sh").read_text(encoding="utf-8"))

    def test_local_repository_is_discovered_after_project_and_repository_moves(self):
        for workflow, writer in self.writers.items():
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                repo = root / "Prism before move"
                self.make_local_repo(repo, workflow)
                project = repo / "projects/Notes/old project"
                project.mkdir(parents=True)
                source = project / ("main.tex" if workflow == "paper-latex" else "draft 中文.md")
                source.write_text("content", encoding="utf-8")
                writer.write_build_script(
                    workflow=workflow,
                    input_path=source,
                    output_path=project / "final result.pdf",
                    project_dir=project,
                    options=["--engine", "auto"],
                )
                moved_project = project.with_name("new 项目")
                project.rename(moved_project)
                moved_repo = repo.with_name("Prism after move")
                repo.rename(moved_repo)
                final_project = moved_repo / moved_project.relative_to(repo)
                result = subprocess.run(
                    [str(final_project / "prism-build.sh")],
                    capture_output=True,
                    text=True,
                    env=self.local_env(root),
                    check=False,
                    timeout=20,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                arguments = json.loads(result.stdout)
                self.assertEqual(arguments[0], "local")
                expected_input = final_project if workflow == "paper-latex" else final_project / source.name
                self.assertEqual(Path(arguments[1]).resolve(), expected_input.resolve())
                self.assertEqual(Path(arguments[3]).resolve(), (final_project / "final result.pdf").resolve())
                self.assertEqual(arguments[-1], "--no-build-script")

    def test_explicit_project_and_skills_overrides_take_precedence(self):
        workflow = "notes-latex"
        writer = self.writers[workflow]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ancestor = root / "ancestor Prism"
            alternate = root / "explicit Prism"
            self.make_local_repo(ancestor, workflow, "ancestor")
            self.make_local_repo(alternate, workflow, "explicit-project")
            standalone = root / "explicit skills"
            self.make_stub(standalone, workflow, "explicit-skills")
            project = ancestor / "projects/Notes/note"
            project.mkdir(parents=True)
            source = project / "note.md"
            source.write_text("content", encoding="utf-8")
            script = writer.write_build_script(
                workflow=workflow,
                input_path=source,
                output_path=project / "note.pdf",
                project_dir=project,
                options=[],
            )
            env = self.local_env(root)
            env["PRISM_PROJECT_DIR"] = str(alternate)
            project_result = subprocess.run([str(script)], capture_output=True, text=True, env=env, check=False, timeout=20)
            self.assertEqual(project_result.returncode, 0, project_result.stderr)
            self.assertEqual(json.loads(project_result.stdout)[0], "explicit-project")
            env["PRISM_LATEX_SKILLS_DIR"] = str(standalone)
            skills_result = subprocess.run([str(script)], capture_output=True, text=True, env=env, check=False, timeout=20)
            self.assertEqual(skills_result.returncode, 0, skills_result.stderr)
            self.assertEqual(json.loads(skills_result.stdout)[0], "explicit-skills")

    def test_invalid_explicit_repository_is_reported_without_fallback(self):
        writer = self.writers["notes-latex"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "note.md"
            source.write_text("content", encoding="utf-8")
            script = writer.write_build_script(
                workflow="notes-latex",
                input_path=source,
                output_path=root / "note.pdf",
                project_dir=root,
                options=[],
            )
            env = self.local_env(root)
            env["PRISM_PROJECT_DIR"] = str(root / "missing repo")
            result = subprocess.run([str(script)], capture_output=True, text=True, env=env, check=False, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PRISM_PROJECT_DIR", result.stderr)
            self.assertIn(str(root / "missing repo"), result.stderr)


if __name__ == "__main__":
    unittest.main()
