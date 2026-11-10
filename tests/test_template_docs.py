from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prism_template_docs", ROOT / "scripts/sync-template-docs.py")
docs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs)


class TemplateDocumentationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.catalog = SimpleNamespace(templates={
            "sample": SimpleNamespace(alias="sample", venue="Synthetic Journal", publisher="Example Press",
                                      article_type="research", article_types=("research", "review"),
                                      guide_path="docs/templates/sample.md"),
            "generic": SimpleNamespace(alias="generic", venue="Generic Draft", publisher=None,
                                       article_type="manuscript", article_types=(),
                                       guide_path="docs/templates/generic.md"),
        })
        blocks = {
            "README.md": ("template-count", "template-catalog"),
            "docs/guide.zh-CN.md": ("template-catalog",),
            "docs/templates.md": ("template-catalog",),
        }
        for relative, names in blocks.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Manual introduction.\n\n" + "\n\n".join(
                f"<!-- prism:{name}:start -->\nstale\n<!-- prism:{name}:end -->" for name in names)
                + "\n\nManual submission guidance.\n")

    def inventory(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_check_is_read_only_and_write_changes_only_marked_blocks(self):
        before = self.inventory()
        self.assertEqual(set(docs.synchronize(self.root, catalog=self.catalog)), set(before))
        self.assertEqual(self.inventory(), before)
        docs.synchronize(self.root, catalog=self.catalog, write=True)
        after = self.inventory()
        self.assertEqual(set(after), set(before))
        for content in after.values():
            self.assertTrue(content.startswith(b"Manual introduction."))
            self.assertTrue(content.endswith(b"Manual submission guidance.\n"))
        self.assertEqual(docs.synchronize(self.root, catalog=self.catalog), ())
        readme = after["README.md"].decode()
        self.assertIn("2 套离线模板", readme)
        self.assertLess(readme.index("Example Press"), readme.index("通用"))
        self.assertIn("[`sample`](docs/templates/sample.md)", readme)
        overview = after["docs/templates.md"].decode()
        self.assertIn("`research`（默认）、`review`", overview)
        self.assertIn("[`sample`](templates/sample.md)", overview)

    def test_invalid_markers_reject_all_writes(self):
        path = self.root / "docs/templates.md"
        path.write_text("<!-- prism:template-catalog:end -->\n<!-- prism:template-catalog:start -->\n")
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "marker order"):
            docs.synchronize(self.root, write=True, catalog=self.catalog)
        self.assertEqual(self.inventory(), before)

    def test_symbolic_link_document_is_rejected(self):
        path = self.root / "docs/templates.md"
        target = self.root / "original.md"
        path.rename(target)
        path.symlink_to(target)
        before = target.read_bytes()
        with self.assertRaisesRegex(ValueError, "symbolic"):
            docs.synchronize(self.root, write=True, catalog=self.catalog)
        self.assertEqual(target.read_bytes(), before)

    def test_real_guides_are_current_and_legacy_anchors_remain(self):
        self.assertEqual(docs.synchronize(ROOT), ())
        overview = (ROOT / "docs/templates.md").read_text()
        for heading in ("NAR", "Angew", "Advanced Science", "Chemical Reviews"):
            self.assertIn(f"## {heading}\n", overview)
        for template in docs.CATALOG.templates.values():
            guide = ROOT / template.guide_path
            self.assertTrue(guide.is_file(), template.alias)
            self.assertIn("[返回模板目录](../templates.md)", guide.read_text())


if __name__ == "__main__":
    unittest.main()
