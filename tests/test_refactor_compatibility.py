"""Fixed starter contracts: the current Prism starter and original journal starters."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from test_renderers import ROOT, load_module

sys.path.insert(0, str(ROOT / "scripts/lib"))
from prism_latex import templates


class RefactorCompatibilityTests(unittest.TestCase):
    def test_starter_files_match_their_explicit_baselines(self):
        baseline = json.loads((ROOT / "tests/fixtures/refactor-baseline.json").read_text())
        with tempfile.TemporaryDirectory(prefix="prism-compatibility-") as temporary:
            for key, expected in baseline["projects"].items():
                alias, kind, language = key.split("/")
                with self.subTest(project=key):
                    target = Path(temporary) / alias / kind / language
                    with contextlib.redirect_stdout(io.StringIO()):
                        templates.initialize(target, False, alias, language=language,
                                             article_type=None if kind == "default" else kind)
                    digest = hashlib.sha256()
                    for path in sorted(target.rglob("*")):
                        if not path.is_file():
                            continue
                        data = path.read_bytes()
                        if path.name == templates.METADATA_NAME:
                            metadata = json.loads(data)
                            metadata.pop("prism_version", None)
                            data = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
                        digest.update(path.relative_to(target).as_posix().encode() + b"\0" + data + b"\0")
                    self.assertEqual(digest.hexdigest(), expected)

    def test_fixed_date_note_and_review_rendering_is_unchanged(self):
        expected = json.loads((ROOT / "tests/fixtures/refactor-baseline.json").read_text())["renderers"]
        notes = load_module("compat_notes", ROOT / "skills/notes-latex/scripts/notes_latex.py")
        reviewer = load_module("compat_reviewer", ROOT / "skills/reviewer-latex/scripts/reviewer_latex.py")
        report = reviewer.parse_report((ROOT / "tests/fixtures/review.md").read_text())
        outputs = {
            "note": notes.render_source(ROOT / "tests/fixtures/note.md", None,
                                        "2026-11-08", "2026-11-08", "xelatex"),
            "author": reviewer.render_report(report, "2026-11-08", "xelatex"),
            "editor": reviewer.render_editor_notes(report, "2026-11-08", "xelatex"),
        }
        for name, value in outputs.items():
            with self.subTest(document=name):
                self.assertEqual(hashlib.sha256(value.encode()).hexdigest(), expected[name])


if __name__ == "__main__":
    unittest.main()
