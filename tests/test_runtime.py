from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from prism_latex.runtime import Artifact, BuildJob, Workspace, execute_build, publish_artifacts
from prism_latex import reviewer


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def test_owned_workspace_cleanup_and_manual_workspace_preservation(self):
        with Workspace("prism-runtime-test.") as workspace:
            owned = workspace.path
            (owned / "main.log").write_text("temporary")
        self.assertFalse(owned.exists())
        manual = self.root / "manual work"
        with self.assertRaisesRegex(RuntimeError, "deliberate"):
            with Workspace("unused", manual) as workspace:
                (workspace.path / "keep.txt").write_text("caller-owned")
                raise RuntimeError("deliberate")
        self.assertEqual((manual / "keep.txt").read_text(), "caller-owned")
        with Workspace("prism-runtime-test.", keep=True) as workspace:
            kept = workspace.path
        self.addCleanup(lambda: __import__("shutil").rmtree(kept))
        self.assertTrue(kept.is_dir())

    def test_executor_uses_explicit_job_and_does_not_publish(self):
        source = self.root / "source"
        source.mkdir()
        work = self.root / "work"
        work.mkdir()
        destination = source / "main.pdf"
        destination.write_bytes(b"old published PDF")
        environment = {"TEXINPUTS": "source//:"}
        job = BuildJob(
            "pdflatex", "main.tex", source, work, env=environment,
            strict=True, outdir_argument=True, compile_log=work / "compile.log",
        )
        environment["TEXINPUTS"] = "changed after construction"

        def run(command, **kwargs):
            self.assertEqual(kwargs["cwd"], source)
            self.assertEqual(kwargs["env"]["TEXINPUTS"], "source//:")
            self.assertIn(f"-outdir={work}", command)
            (work / "main.pdf").write_bytes(b"new compiled PDF")
            (work / "main.log").write_text("LaTeX Warning: Synthetic warning.\n")
            return subprocess.CompletedProcess(command, 0, "compiler stdout")

        with mock.patch("prism_latex.runtime.subprocess.run", side_effect=run):
            result = execute_build(job)
        self.assertEqual(result.pdf, work / "main.pdf")
        self.assertEqual(result.warnings, ("LaTeX Warning: Synthetic warning.",))
        self.assertEqual((work / "compile.log").read_text(), "compiler stdout")
        self.assertEqual(destination.read_bytes(), b"old published PDF")

    def test_executor_enforces_failure_pdf_and_strict_checks(self):
        job = BuildJob("xelatex", "main.tex", self.root, self.root, strict=True)
        for mode in ("failure", "missing-pdf", "strict"):
            with self.subTest(mode=mode):
                (self.root / "main.pdf").unlink(missing_ok=True)

                def run(command, **kwargs):
                    if mode == "strict":
                        (self.root / "main.pdf").write_bytes(b"PDF")
                        (self.root / "main.log").write_text("Missing character: synthetic")
                    return subprocess.CompletedProcess(command, int(mode == "failure"), "synthetic failure")

                with mock.patch("prism_latex.runtime.subprocess.run", side_effect=run):
                    with self.assertRaises(SystemExit):
                        execute_build(job)

    def make_artifacts(self, *, existing: bool = True):
        work = self.root / "work"
        outputs = self.root / "outputs"
        work.mkdir(exist_ok=True)
        outputs.mkdir(exist_ok=True)
        result = []
        for role in ("author", "editor"):
            source = work / f"{role}.pdf"
            source.write_bytes(f"new {role}".encode())
            destination = outputs / source.name
            if existing:
                destination.write_bytes(f"old {role}".encode())
            result.append(Artifact(source, destination))
        return result

    def fail_second_replace(self, artifacts):
        replace = os.replace
        failed = False

        def replace_once(source, destination):
            nonlocal failed
            if Path(destination) == artifacts[1].destination and not failed:
                failed = True
                raise OSError("deliberate second-publication failure")
            return replace(source, destination)

        return mock.patch("prism_latex.runtime.os.replace", side_effect=replace_once)

    def test_publication_rolls_back_first_file_if_second_replacement_fails(self):
        artifacts = self.make_artifacts()
        with self.fail_second_replace(artifacts):
            with self.assertRaisesRegex(OSError, "second-publication"):
                publish_artifacts(artifacts)
        for role, artifact in zip(("author", "editor"), artifacts):
            self.assertEqual(artifact.destination.read_bytes(), f"old {role}".encode())
        self.assertEqual(sorted(p.name for p in artifacts[0].destination.parent.iterdir()), ["author.pdf", "editor.pdf"])

    def test_publication_rolls_back_new_file_and_only_copies_explicit_artifacts(self):
        artifacts = self.make_artifacts(existing=False)
        secret = artifacts[0].source.parent / "unselected-confidential.pdf"
        secret.write_bytes(b"private synthetic material")
        with self.fail_second_replace(artifacts):
            with self.assertRaises(OSError):
                publish_artifacts(artifacts)
        self.assertEqual(list(artifacts[0].destination.parent.iterdir()), [])
        publish_artifacts(artifacts[:1])
        self.assertEqual(list(artifacts[0].destination.parent.iterdir()), [artifacts[0].destination])

    def test_invalid_publication_plan_is_rejected_before_output_changes(self):
        artifacts = self.make_artifacts()
        for batch in (
            [artifacts[0], artifacts[0]],
            [Artifact(self.root / "absent.pdf", artifacts[0].destination)],
            [Artifact(artifacts[0].destination, artifacts[0].destination)],
        ):
            with self.subTest(batch=batch):
                with self.assertRaises(ValueError):
                    publish_artifacts(batch)
                self.assertEqual(artifacts[0].destination.read_bytes(), b"old author")

    def test_reviewer_dual_tex_publication_rolls_back_without_tex_lookup(self):
        draft = self.root / "draft.md"
        draft.write_text("# Synthetic review\n\n## Overall\nPublic assessment.\n\n## 给编辑的保密意见\nSynthetic private marker.\n")
        author = self.root / "author.tex"
        editor = self.root / "author_editor_notes.tex"
        author.write_text("old author")
        editor.write_text("old editor")
        artifacts = [Artifact(draft, author), Artifact(draft, editor)]
        with self.fail_second_replace(artifacts):
            with mock.patch.object(reviewer, "choose_engine", side_effect=AssertionError("TeX lookup")):
                with self.assertRaises(OSError):
                    reviewer.main([str(draft), "--no-compile", "--out", str(author)])
        self.assertEqual(author.read_text(), "old author")
        self.assertEqual(editor.read_text(), "old editor")

    def test_reviewer_dual_pdf_publication_rolls_back_after_both_compile(self):
        draft = self.root / "draft.md"
        draft.write_text("## Overall\nPublic assessment.\n\n## Confidential comments to editor\nSynthetic private marker.\n")
        author = self.root / "author.pdf"
        editor = self.root / "author_editor_notes.pdf"
        author.write_bytes(b"old author")
        editor.write_bytes(b"old editor")
        artifacts = [Artifact(draft, author), Artifact(draft, editor)]
        compiled = []

        def compile_tex(path, engine, strict):
            compiled.append(path.name)
            output = path.with_suffix(".pdf")
            output.write_bytes(path.read_bytes())
            return output, ""

        with self.fail_second_replace(artifacts):
            with mock.patch.object(reviewer, "choose_engine", return_value="xelatex"):
                with mock.patch.object(reviewer, "compile_tex", side_effect=compile_tex):
                    with self.assertRaises(OSError):
                        reviewer.main([str(draft), "--out", str(author)])
        self.assertEqual(len(compiled), 2)
        self.assertEqual(author.read_bytes(), b"old author")
        self.assertEqual(editor.read_bytes(), b"old editor")


if __name__ == "__main__":
    unittest.main()
