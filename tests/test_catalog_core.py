"""Small injected catalogs exercise contracts without mirroring production data."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from prism_latex.catalog import (CATALOG, BuildProfile, DocumentRole, SourceReference,
                                 TemplateCatalog, TemplateDefinition)
from prism_latex.initialization import apply_initialization, plan_initialization
from prism_latex.project import load_project_config
from prism_latex.template_assets import AssetContext


class CatalogCoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="prism-small-catalog-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.assets = self.root / "assets"
        self.assets.mkdir()
        self.record = TemplateDefinition(
            alias="example", id="journal/example", kind="journal", venue="Example Journal",
            publisher="Example Press", article_type="research", article_types=("research", "review"),
            backend="plain", directory="example", engine="pdflatex", description="Synthetic test fixture",
            guide_path="docs/example.md", documents=(DocumentRole("main", "main.tex"),
                                                       DocumentRole("supplementary", "supplementary.tex")),
            sources=(SourceReference("Example", "https://example.org/template"),),
        )
        self.catalog = TemplateCatalog({"example": self.record},
                                       {"plain": BuildProfile(("article.cls",), None, False,
                                                              required_common=("supplementary.tex", "references.bib"))})
        common = self.assets / "example" / "common"
        common.mkdir(parents=True)
        for name in ("supplementary.tex", "references.bib"):
            (common / name).write_text("% synthetic shared content\n")
        for article in ("research", "review"):
            path = self.assets / "example" / article
            path.mkdir()
            (path / "main.tex").write_text(f"% selected {article}\n")
        self.context = AssetContext(self.assets)

    def test_definitions_and_nested_profile_selections_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.record.venue = "Changed"
        with self.assertRaises(TypeError):
            self.catalog.templates["another"] = self.record
        profile = BuildProfile((), None, False, bundled=("test", {"original.cls": "copy.cls"}))
        with self.assertRaises(TypeError):
            profile.bundled[1]["other"] = "x"
        with self.assertRaises(TypeError):
            self.context.science_sha256["x"] = "y"

    def test_invalid_model_fields_fail_at_registration(self):
        cases = ({"id": None}, {"alias": None}, {"article_type": "../escape"},
                 {"backend": "../profile"}, {"edition": True}, {"track": 7}, {"stage": ""},
                 {"id": "family/example"}, {"directory": "../escape"},
                 {"guide_path": "/private/guide.md"}, {"engine": "shell"},
                 {"article_types": ["research"]}, {"article_types": ("review",)},
                 {"documents": (DocumentRole("main", "main.tex"), DocumentRole("main", "other.tex"))})
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.record, **changes)
        with self.assertRaises(ValueError):
            TemplateCatalog({"example": self.record}, {})
        with self.assertRaises(ValueError):
            BuildProfile((), None, False, shared_assets=("../../outside.cls",))
        with self.assertRaises(ValueError):
            DocumentRole("main", "folder/../secret.tex")
        with self.assertRaises(ValueError):
            DocumentRole(1, "main.tex")
        with self.assertRaises(ValueError):
            SourceReference(1, "https://example.org/template")

    def test_project_configuration_reads_metadata_once_without_rewriting(self):
        path = self.root / "prism-template.json"
        metadata = {"schema_version": 1, "template": "journal/example", "template_id": "journal/example",
                    "engine": "unused-stored-engine", "language": "english"}
        content = json.dumps(metadata)
        path.write_text(content)
        original_read = Path.read_text
        reads = []
        def observed(path, *args, **kwargs):
            reads.append(path)
            return original_read(path, *args, **kwargs)
        with mock.patch.object(Path, "read_text", observed):
            config = load_project_config(self.root, catalog=self.catalog)
        self.assertEqual(reads, [path])
        self.assertEqual((config.template, config.article_type, config.language, config.variant),
                         ("example", "research", "english", None))
        self.assertEqual(path.read_text(), content)
        with self.assertRaises(FrozenInstanceError):
            config.language = "bilingual"
        path.unlink()
        self.assertIsNone(load_project_config(self.root, catalog=self.catalog).template)

    def test_initialization_plan_is_read_only_and_selects_one_content_recipe(self):
        destination = self.root / "not created" / "中文稿件"
        plan = plan_initialization(destination, False, "example", language="english", article_type="review",
                                   catalog=self.catalog, context=self.context)
        self.assertFalse(destination.parent.exists())
        generated = {file.path: file.content for file in plan.files}
        self.assertEqual(generated["main.tex"], b"% selected review\n")
        self.assertNotIn("research/main.tex", generated)
        metadata = json.loads(generated["prism-template.json"])
        self.assertEqual(metadata["article_type"], "review")
        self.assertEqual(metadata["engine"], "pdflatex")
        apply_initialization(plan)
        self.assertEqual((destination / "main.tex").read_bytes(), generated["main.tex"])
        self.assertFalse(list(destination.parent.glob(".*.prism-init-*")))

    def test_missing_selected_or_common_resource_never_changes_target(self):
        destination = self.root / "existing"
        destination.mkdir()
        marker = destination / "keep.txt"
        marker.write_bytes(b"synthetic local material")
        missing = self.assets / "example" / "common" / "supplementary.tex"
        missing.unlink()
        with self.assertRaisesRegex(SystemExit, "assets are missing"):
            plan_initialization(destination, True, "example", language="english",
                                catalog=self.catalog, context=self.context)
        self.assertEqual(list(destination.iterdir()), [marker])
        self.assertFalse(destination.with_name("existing.backup").exists())

    def test_asset_changes_after_planning_abort_before_target_mutation(self):
        destination = self.root / "existing"
        destination.mkdir()
        marker = destination / "keep.txt"
        marker.write_bytes(b"synthetic local material")
        plan = plan_initialization(destination, True, "example", language="english",
                                   catalog=self.catalog, context=self.context)
        (self.assets / "example" / "research" / "main.tex").write_text("changed asset\n")
        with self.assertRaisesRegex(SystemExit, "assets changed"):
            apply_initialization(plan)
        self.assertEqual(marker.read_bytes(), b"synthetic local material")
        self.assertFalse(destination.with_name("existing.backup").exists())

    def test_symlink_assets_are_rejected_before_directory_creation(self):
        source = self.assets / "example" / "research" / "main.tex"
        source.unlink()
        source.symlink_to(self.assets / "example" / "review" / "main.tex")
        destination = self.root / "missing" / "target"
        with self.assertRaises(SystemExit):
            plan_initialization(destination, False, "example", language="english",
                                catalog=self.catalog, context=self.context)
        self.assertFalse(destination.parent.exists())

    def test_symlink_recipe_directory_is_rejected_before_target_changes(self):
        source = self.assets / "example"
        original = source.with_name("original-assets")
        source.rename(original)
        source.symlink_to(original, target_is_directory=True)
        destination = self.root / "missing" / "target"
        with self.assertRaisesRegex(SystemExit, "symbolic links"):
            plan_initialization(destination, False, "example", language="english",
                                catalog=self.catalog, context=self.context)
        self.assertFalse(destination.parent.exists())

    def test_details_report_capabilities_roles_and_only_relative_paths(self):
        detail = self.catalog.detail("journal/example")
        self.assertEqual(detail["schema_version"], 1)
        self.assertEqual(detail["default_article_type"], "research")
        self.assertTrue(detail["capabilities"]["article_type_selection"])
        self.assertFalse(detail["capabilities"]["official_package_import"])
        self.assertEqual(detail["documents"][0]["path"], "main.tex")
        self.assertNotIn(str(self.root), json.dumps(detail))
        self.assertFalse(CATALOG.detail("chemrev")["capabilities"]["article_type_selection"])
        self.assertTrue(CATALOG.detail("nature")["capabilities"]["official_package_import"])

    def test_controlled_catalog_validation_checks_resources_and_guides_without_tex(self):
        (self.assets / "prism-cjk.sty").write_text("% synthetic CJK fixture\n")
        guide = self.root / "docs" / "example.md"
        guide.parent.mkdir()
        guide.write_text("# Example\n[Reference](../reference.md)\n")
        (self.root / "reference.md").write_text("# Reference\n")
        with mock.patch("subprocess.run", side_effect=AssertionError("No compiler allowed")):
            self.assertEqual(self.catalog.validate(self.root, self.assets), ())
        required = self.assets / "example" / "layout.sty"
        record = replace(self.record, required_assets=("layout.sty",))
        catalog = TemplateCatalog({"example": record}, self.catalog.profiles)
        issues = catalog.validate(self.root, self.assets)
        self.assertTrue(any("layout.sty" in issue for issue in issues), issues)
        required.write_text("% synthetic style\n")
        self.assertEqual(catalog.validate(self.root, self.assets), ())
        guide.write_text("# Example\n[Missing](missing.md)\n")
        self.assertTrue(any("guide link" in issue for issue in catalog.validate(self.root, self.assets)))
        guide.write_text("# Example\n")
        main = self.assets / "example" / "review" / "main.tex"
        main.unlink()
        self.assertTrue(any("review/main.tex" in issue for issue in catalog.validate(self.root, self.assets)))

    def test_real_catalog_offline_validation_includes_prism_style_and_sections(self):
        self.assertEqual(CATALOG.validate(), ())
        # Do not duplicate production registration to synthesize expectations.
        # This required local style is a dependency of Prism's unchanged main.
        prism = CATALOG.templates["prism"]
        self.assertIn("prism-paper.sty", prism.required_assets)
        self.assertIn("sections/results.tex", prism.required_assets)

    def test_real_catalog_has_complete_all_language_recipe_declarations(self):
        self.assertEqual(len(CATALOG.templates), 20)
        for alias, definition in CATALOG.templates.items():
            with self.subTest(alias=alias):
                detail = CATALOG.detail(alias)
                self.assertEqual(set(detail["languages"]), {"bilingual", "english"})
                self.assertEqual(detail["bibliography"], "bibtex")
                self.assertIn(definition.article_type, detail["article_types"])
                self.assertEqual({role.role for role in definition.documents} >= {"main", "supplementary", "examples"}, True)
                for article in definition.article_types or (definition.article_type,):
                    self.assertEqual(CATALOG.article_type(alias, article if definition.article_types else None), article)


if __name__ == "__main__":
    unittest.main()
