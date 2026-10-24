from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    # Each workflow must resolve its own compatibility imports. A previous
    # workflow's short module names must not mask a broken local helper.
    helpers = {key: sys.modules.pop(key, None) for key in ("build_support", "build_script")}
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)
        for key, previous in helpers.items():
            sys.modules.pop(key, None)
            if previous is not None:
                sys.modules[key] = previous


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notes = load_module(
            "prism_notes", ROOT / "skills/notes-latex/scripts/notes_latex.py"
        )
        cls.reviewer = load_module(
            "prism_reviewer", ROOT / "skills/reviewer-latex/scripts/reviewer_latex.py"
        )

    def test_note_long_table_and_portable_fonts(self):
        source = ROOT / "tests/fixtures/note.md"
        rendered = self.notes.render_source(source, None, None, None, "xelatex")
        self.assertIn(r"\begin{longtable}", rendered)
        self.assertIn("texgyretermes-regular.otf", rendered)
        self.assertIn("FandolSong-Regular.otf", rendered)
        self.assertNotIn("Songti SC", rendered)

    def test_reviewer_confidential_notes_are_separate(self):
        text = (ROOT / "tests/fixtures/review.md").read_text(encoding="utf-8")
        report = self.reviewer.parse_report(text)
        author_tex = self.reviewer.render_report(report, "2026-08-04", "xelatex")
        editor_tex = self.reviewer.render_editor_notes(report, "2026-08-04", "xelatex")
        confidential = "This sentence is confidential"
        self.assertNotIn(confidential, author_tex)
        self.assertIsNotNone(editor_tex)
        self.assertIn(confidential, editor_tex)
        self.assertIn(r"\reviewpointheading{1}{Validation design}", author_tex)
        self.assertIn(r"\reviewpointheading{2}{Traceability}", author_tex)
        self.assertIn(r"\reviewplainpoint{3}", author_tex)

    def test_strict_check_rejects_final_layout_errors(self):
        with self.assertRaises(SystemExit):
            self.notes.enforce_strict("Overfull \\hbox (5.0pt too wide)")

    def test_reviewer_default_basename_is_portable(self):
        self.assertEqual(
            self.reviewer.default_basename(Path("review draft 中文.md")),
            "review-draft",
        )
        self.assertEqual(self.reviewer.default_basename(Path("中文.md")), "review")

    def test_workflows_share_build_and_font_helpers(self):
        paper = load_module(
            "prism_paper", ROOT / "skills/paper-latex/scripts/paper_latex.py"
        )
        self.assertEqual(self.notes.choose_engine.__module__, "prism_latex.build_support")
        self.assertIs(self.notes.choose_engine, self.reviewer.choose_engine)
        self.assertIs(self.notes.choose_engine, paper.choose_engine)
        self.assertIs(self.notes.portable_font_setup, self.reviewer.font_setup)
        self.assertIs(self.notes.write_build_script, paper.write_build_script)


if __name__ == "__main__":
    unittest.main()
