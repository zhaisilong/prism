from __future__ import annotations

import concurrent.futures
import json
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
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from prism_latex import templates

PAPER = ROOT / "scripts" / "latex-paper.sh"
NOTE = ROOT / "scripts" / "latex-note.sh"
REVIEW = ROOT / "scripts" / "latex-review.sh"
INTERMEDIATES = {".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".log", ".out", ".spl", ".toc"}


class BilingualTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="prism-bilingual-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.work = self.root / "临时 work"
        self.work.mkdir()
        self.env = os.environ.copy()
        self.env.update(TMPDIR=str(self.work), PYTHONDONTWRITEBYTECODE="1")
        for key in ("PRISM_PROJECT_DIR", "PRISM_LATEX_SKILLS_DIR"):
            self.env.pop(key, None)

    def cli(self, wrapper, *arguments, env=None, timeout=180):
        return subprocess.run(
            [str(wrapper), *(str(item) for item in arguments)],
            capture_output=True, text=True, check=False,
            env=self.env if env is None else env, timeout=timeout,
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_clean(self, project):
        self.assertEqual(
            [str(path.relative_to(project)) for path in project.rglob("*")
             if path.is_file() and path.suffix.lower() in INTERMEDIATES],
            [],
        )

    def require_real_tex(self):
        for command in ("xelatex", "pdflatex", "latexmk", "bibtex", "kpsewhich", "pdftotext"):
            if not shutil.which(command):
                self.skipTest(f"Real bilingual tests require {command}")
        for resource in ("xeCJK.sty", "FandolSong-Regular.otf", "FandolHei-Regular.otf",
                         "achemso.sty", "elsarticle.cls"):
            probe = subprocess.run(["kpsewhich", resource], capture_output=True, text=True, check=False)
            if probe.returncode or not probe.stdout.strip():
                self.skipTest(f"Real bilingual tests require {resource}")

    def text_of(self, pdf):
        return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True,
                              text=True, check=True, timeout=30).stdout

    def test_nine_defaults_are_offline_bilingual_and_support_aliases(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network")) as fetch:
            for alias, record in templates.TEMPLATES.items():
                with self.subTest(template=alias):
                    target = self.root / "中文 projects with spaces" / alias
                    templates.initialize(target, False, record["id"])
                    metadata = json.loads((target / templates.METADATA_NAME).read_text())
                    self.assertEqual(metadata["template"], alias)
                    self.assertEqual(metadata["template_id"], record["id"])
                    self.assertEqual(metadata["language"], "bilingual")
                    self.assertEqual(templates.template_language_for_project(target), "bilingual")
                    engine = templates.template_engine(alias, "auto", "bilingual")
                    self.assertIn(engine, ("auto", "xelatex") if alias == "prism" else ("xelatex",))
                    if alias != "prism":
                        self.assertTrue((target / "prism-cjk.sty").is_file())
                        self.assertIn("prism-cjk", (target / "main.tex").read_text())
                        if alias != "science-advances":
                            self.assertIn("prism-cjk", (target / "supplementary.tex").read_text())
                    self.assertIn("prism-cjk", (target / "examples.tex").read_text())
                    self.assertNotIn(str(self.root), json.dumps(metadata))
        fetch.assert_not_called()

    def test_english_and_legacy_projects_preserve_pdflatex_and_metadata(self):
        for alias in ("nature", "bib", "science-advances", "jacs"):
            with self.subTest(template=alias):
                target = self.root / f"english-{alias}"
                self.assert_success(self.cli(PAPER, "--init", target, "--template", alias, "--language", "english"))
                metadata_path = target / templates.METADATA_NAME
                metadata = json.loads(metadata_path.read_text())
                self.assertEqual(metadata["language"], "english")
                self.assertEqual(templates.template_engine(alias, "auto", "english"), "pdflatex")
                packages = templates.template_packages(alias, "auto", language="english")
                self.assertNotIn("xeCJK.sty", packages)
                self.assertFalse((target / "prism-cjk.sty").exists())
                legacy = dict(metadata)
                legacy.pop("language")
                original = (json.dumps(legacy, ensure_ascii=False) + "\n").encode()
                metadata_path.write_bytes(original)
                self.assertIsNone(templates.template_language_for_project(target))
                self.assertEqual(templates.template_engine(alias, "auto", None), "pdflatex")
                self.assertEqual(templates.template_engine(alias, "xelatex", None), "xelatex")
                self.assertEqual(metadata_path.read_bytes(), original)

    def test_language_check_deps_and_rejection_are_nonmutating(self):
        fake_bin = self.root / "fake bin"
        fake_bin.mkdir()
        env = self.env.copy()
        env["PATH"] = str(fake_bin)
        entrypoint = ROOT / "skills" / "paper-latex" / "scripts" / "paper_latex.py"
        def check(*args):
            return subprocess.run([sys.executable, "-B", str(entrypoint), *map(str, args)],
                                  capture_output=True, text=True, env=env, timeout=30)
        mixed = check("--check-deps", "--template", "bib", "--language", "bilingual")
        self.assertNotEqual(mixed.returncode, 0)
        self.assertIn("xelatex: MISSING", mixed.stdout)
        self.assertIn("xeCJK.sty: MISSING", mixed.stdout)
        self.assertIn("FandolSong-Regular.otf: MISSING", mixed.stdout)
        english = check("--check-deps", "--template", "bib", "--language", "english")
        self.assertNotEqual(english.returncode, 0)
        self.assertIn("pdflatex: MISSING", english.stdout)
        self.assertNotIn("xeCJK", english.stdout)
        self.assertNotIn("Fandol", english.stdout)
        target = self.root / "existing source"
        target.mkdir()
        original = target / "manuscript.tex"
        original.write_text("keep existing source")
        rejected = self.cli(PAPER, "--init", target, "--template", "nature")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(original.read_text(), "keep existing source")
        self.assertFalse(target.with_name(target.name + ".backup").exists())
        self.assert_success(self.cli(PAPER, "--init", target, "--template", "nature", "--force"))
        self.assertEqual((target.with_name(target.name + ".backup") / "manuscript.tex").read_text(),
                         "keep existing source")
        metadata = (target / templates.METADATA_NAME).read_bytes()
        source = (target / "main.tex").read_bytes()
        checked = check(target, "--check-deps", "--language", "english")
        self.assertIn("pdflatex: MISSING", checked.stdout)
        self.assertEqual((target / templates.METADATA_NAME).read_bytes(), metadata)
        self.assertEqual((target / "main.tex").read_bytes(), source)

    def test_bilingual_dependency_check_reports_local_style_not_global(self):
        target = self.root / "local dependency"
        self.assert_success(self.cli(PAPER, "--init", target, "--template", "nature"))
        metadata = (target / templates.METADATA_NAME).read_bytes()
        style = target / "prism-cjk.sty"
        content = style.read_bytes()
        found = self.cli(PAPER, target, "--check-deps")
        self.assertIn(str(style), found.stdout)
        style.unlink()
        missing = self.cli(PAPER, target, "--check-deps")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("prism-cjk.sty: MISSING", missing.stdout)
        style.write_bytes(content)
        checked = self.cli(PAPER, target, "--check-deps", "--language", "english")
        self.assertNotIn("prism-cjk.sty: MISSING", checked.stdout)
        self.assertEqual((target / templates.METADATA_NAME).read_bytes(), metadata)

    def test_chinese_review_separates_editor_material_and_blocks_unknown_labels(self):
        self.require_real_tex()
        source = self.root / "review.md"
        source.write_text("期刊：Example Journal\n稿件标题：中文与 English 标题\n## 总体意见\n作者可以看到 AuthorVisible。\n## 主要问题\n请补充细节。\n## 给编辑的保密意见\nEditorOnlySentinel 保密文字。\n", encoding="utf-8")
        for no_compile in (True, False):
            with self.subTest(no_compile=no_compile):
                output = self.root / ("review-tex" if no_compile else "review-pdf")
                output.mkdir()
                args = [source, "--outdir", output, "--no-build-script"]
                if no_compile:
                    args.append("--no-compile")
                else:
                    args.append("--strict")
                result = self.cli(REVIEW, *args)
                self.assert_success(result)
                suffix = ".tex" if no_compile else ".pdf"
                author = output / f"review{suffix}"
                editor = output / f"review_editor_notes{suffix}"
                author_text = author.read_text() if no_compile else self.text_of(author)
                editor_text = editor.read_text() if no_compile else self.text_of(editor)
                self.assertIn("AuthorVisible", author_text)
                self.assertNotIn("EditorOnlySentinel", author_text)
                self.assertIn("EditorOnlySentinel", editor_text)
        source.write_text("## 总体意见\n作者正文。\n## 仅供编辑参考的其他补充\nEditorOnlySentinel\n", encoding="utf-8")
        for no_compile in (True, False):
            suffix = ".tex" if no_compile else ".pdf"
            output = self.root / ("blocked-tex" if no_compile else "blocked-pdf")
            output.mkdir()
            existing = output / f"review{suffix}"
            existing.write_bytes(b"original output")
            args = [source, "--outdir", output, "--no-build-script"]
            if no_compile:
                args.append("--no-compile")
            result = self.cli(REVIEW, *args)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(existing.read_bytes(), b"original output")
            self.assertFalse((output / f"review_editor_notes{suffix}").exists())

    def test_note_english_body_with_generated_chinese_date_and_title(self):
        self.require_real_tex()
        source = self.root / "english-note.md"
        source.write_text("Plain English body and an equation $x=1$.\n", encoding="utf-8")
        for label, options in (("english", []), ("chinese-title", ["--title", "中文标题 English"])):
            output = self.root / f"{label}.pdf"
            result = self.cli(NOTE, source, "--out", output, "--strict", "--no-build-script", *options)
            self.assert_success(result)
            text = self.text_of(output)
            self.assertIn("创建日期", text)
            self.assertIn("更新日期", text)
            if options:
                self.assertIn("中文标题", text)
            self.assert_clean(source.parent)
    def test_ambiguous_editor_labels_stop_before_any_output(self):
        cases = ("标题（仅供编辑）：EditorOnlySentinel", "## 总体意见 / Confidential comments to editor\nEditorOnlySentinel", "## 给编者的特殊资料\nEditorOnlySentinel")
        for index, case in enumerate(cases):
            with self.subTest(case=index):
                source = self.root / f"review-{index}.md"
                source.write_text("## 总体意见\n作者正文。\n" + case + "\n", encoding="utf-8")
                output = self.root / f"blocked-{index}"
                output.mkdir()
                author = output / f"review-{index}.tex"
                editor = output / f"review-{index}_editor_notes.tex"
                author.write_bytes(b"author before")
                editor.write_bytes(b"editor before")
                result = self.cli(REVIEW, source, "--outdir", output, "--no-compile")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(author.read_bytes(), b"author before")
                self.assertEqual(editor.read_bytes(), b"editor before")

    def test_all_default_templates_compile_synthetic_chinese_in_main_and_supplements(self):
        self.require_real_tex()
        def check_template(alias):
            project = self.root / "论文 projects" / alias
            self.assert_success(self.cli(PAPER, "--init", project, "--template", alias))
            files = ["main.tex", "examples.tex"]
            if alias != "science-advances":
                files.append("supplementary.tex")
            for name in files:
                path = project / name
                text = path.read_text(encoding="utf-8")
                text = re.sub(r"(\\title(?:\[[^\]]*\])?\{)", lambda m: m.group(1) + "中英标题 ", text, count=1)
                if name == "main.tex" and alias == "prism":
                    text = text.replace(r"\newcommand{\papertitle}{", r"\newcommand{\papertitle}{中英标题 ", 1)
                text = text.replace("First Author", "中文作者 First Author", 1)
                snippet = ("\n\\section{中文章节 Mixed}\n中文正文 English text。\\n"
                           "\\begin{figure}[htbp]\\centering\\fbox{Example}"
                           "\\caption{中文图注 Mixed caption}\\end{figure}\n"
                           "\\begin{table}[htbp]\\centering\\caption{中文表格 Mixed table}"
                           "\\begin{tabular}{ll}中文表头 & Value\\\\数据 & 1\\end{tabular}\\end{table}\n"
                           "\\[x=\\text{中文公式}\\]\n")
                # Use an actual newline after the sample sentence.
                snippet = snippet.replace(r"。\n", "。\n")
                self.assertIn(r"\end{document}", text)
                path.write_text(text.replace(r"\end{document}", snippet + r"\end{document}", 1), encoding="utf-8")
                args = [project, "--main", name, "--strict"]
                if name != "main.tex":
                    args.append("--no-build-script")
                result = self.cli(PAPER, *args)
                self.assert_success(result)
                extracted = self.text_of(project / Path(name).with_suffix(".pdf"))
                for expected in ("中文正文", "中文图注", "中文表格", "中文表头", "中文公式"):
                    self.assertIn(expected, extracted, f"{alias}/{name}: {expected}")
                if name == "main.tex":
                    self.assertIn("中英标题", extracted)
                    self.assertIn("中文作者", extracted)
                    self.assertTrue((project / "prism-build.sh").exists())
                self.assert_clean(project)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(check_template, alias): alias for alias in templates.TEMPLATES}
            for future in concurrent.futures.as_completed(futures):
                with self.subTest(template=futures[future]):
                    future.result()
    def test_editor_heading_aliases_keep_private_material_separate(self):
        for index, heading in enumerate(("给编者的意见", "致编者的保密意见", "给主编的意见", "給主編的保密意見")):
            with self.subTest(heading=heading):
                source = self.root / f"alias-{index}.md"
                source.write_text(f"## 总体意见\nAuthorVisible\n## {heading}\nEditorOnlySentinel\n", encoding="utf-8")
                result = self.cli(REVIEW, source, "--no-compile", "--no-build-script")
                self.assert_success(result)
                author = source.with_suffix(".tex").read_text()
                editor = source.with_name(source.stem + "_editor_notes.tex").read_text()
                self.assertIn("AuthorVisible", author)
                self.assertNotIn("EditorOnlySentinel", author)
                self.assertIn("EditorOnlySentinel", editor)
    def test_english_journal_mode_really_compiles_with_pdflatex(self):
        self.require_real_tex()
        def check_template(alias):
            project = self.root / "English journals" / alias
            self.assert_success(self.cli(PAPER, "--init", project, "--template", alias, "--language", "english"))
            metadata = json.loads((project / templates.METADATA_NAME).read_text())
            self.assertEqual(metadata["engine"], "pdflatex")
            self.assertNotIn("prism-cjk", (project / "main.tex").read_text())
            self.assert_success(self.cli(PAPER, project, "--strict", "--no-build-script"))
            self.assertIn("Peng" if alias == "science-advances" else "Wilkinson", self.text_of(project / "main.pdf"))
            self.assert_clean(project)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(check_template, alias): alias for alias in ("nature", "bib", "ddt", "jcim", "science-advances")}
            for future in concurrent.futures.as_completed(futures):
                with self.subTest(template=futures[future]):
                    future.result()

    def test_prism_lualatex_main_and_examples_with_chinese(self):
        self.require_real_tex()
        if not shutil.which("lualatex"):
            self.skipTest("LuaLaTeX is not installed")
        resource = subprocess.run(["kpsewhich", "luatexja-fontspec.sty"], capture_output=True, text=True)
        if resource.returncode or not resource.stdout.strip():
            self.skipTest("luatexja-fontspec is not installed")
        cache = self.root / "font cache"
        cache.mkdir()
        self.env.update(TEXMFCACHE=str(cache), TEXMFVAR=str(cache), XDG_CACHE_HOME=str(cache))
        project = self.root / "Lua 中文 paper"
        self.assert_success(self.cli(PAPER, "--init", project, "--template", "prism"))
        for name in ("main.tex", "supplementary.tex", "examples.tex"):
            path = project / name
            text = path.read_text()
            path.write_text(text.replace(r"\end{document}", "\n中文验证 Lua test。\n" + r"\end{document}", 1))
            result = self.cli(PAPER, project, "--main", name, "--engine", "lualatex", "--strict", "--no-build-script", timeout=300)
            self.assert_success(result)
            self.assertIn("中文验证", self.text_of(project / Path(name).with_suffix(".pdf")))
        self.assert_clean(project)
