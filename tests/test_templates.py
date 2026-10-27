from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from prism_latex import build_support, templates


class VersionTests(unittest.TestCase):
    def test_calendar_versions_and_same_day_revisions(self):
        for version in ("2026.10.24", "2026.10.24.1", "2024.02.29.12"):
            with self.subTest(version=version), mock.patch.object(Path, "read_text", return_value=version + "\n"):
                self.assertEqual(build_support.project_version(), version)
        for version in ("1.0.0", "2026.02.29", "2026.10.24.0", "2026.10.24.01", "2026.1.1", "2026.10.24\nextra"):
            with self.subTest(version=version), mock.patch.object(Path, "read_text", return_value=version):
                with self.assertRaises(SystemExit):
                    build_support.project_version()

    def test_all_clis_report_root_version_without_a_compiler(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = os.environ.copy()
            env.update(PATH=temporary, PYTHONDONTWRITEBYTECODE="1")
            env.pop("PRISM_PROJECT_DIR", None)
            Path(temporary, "python3").symlink_to(sys.executable)
            Path(temporary, "dirname").symlink_to(shutil.which("dirname"))
            expected = f"Prism {ROOT.joinpath('VERSION').read_text().strip()}\n"
            for wrapper in ("latex-note.sh", "latex-review.sh", "latex-paper.sh"):
                with self.subTest(wrapper=wrapper):
                    result = subprocess.run(["/bin/bash", str(ROOT / "scripts" / wrapper), "--version"], env=env, capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, expected)


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.asset_dir = self.root / "assets"
        for name in ("paper-template", "nature-template", "nature-communications-template", "bib-template", "ddt-template", "jcim-template", "science-advances-template"):
            asset = self.asset_dir / name
            asset.mkdir(parents=True)
            (asset / "main.tex").write_text(f"% {name}\n", encoding="utf-8")
        (self.asset_dir / "paper-template" / "examples.tex").write_text("% shared standalone examples\n")
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(templates, "ASSET_DIR", self.asset_dir).start()

    def package(self, *, template: str = "nature", missing: str | None = None, symlink: str | None = None) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            required = templates.NATURE_MEMBERS if template == "nature" else templates.BIB_MEMBERS
            for member in required:
                if member == missing:
                    continue
                if member == symlink:
                    info = zipfile.ZipInfo(member)
                    info.create_system = 3
                    info.external_attr = 0o120777 << 16
                    archive.writestr(info, "elsewhere")
                else:
                    archive.writestr(member, f"official fixture {member}")
            archive.writestr("../../not-extracted.txt", "unsafe path")
            archive.writestr("sn-article-template/install.sh", "exit 1")
        return buffer.getvalue()

    def pinned_source(self, archive: bytes, template: str = "nature") -> Path:
        source = self.root / "official package.zip"
        source.write_bytes(archive)
        mock.patch.object(templates, f"{template.upper()}_SIZE", len(archive)).start()
        mock.patch.object(templates, f"{template.upper()}_SHA256", hashlib.sha256(archive).hexdigest()).start()
        return source

    def test_default_initialization_is_portable_and_preserves_assets(self):
        destination = self.root / "论文 with spaces" / "new paper"
        templates.initialize(destination, False)
        self.assertEqual((destination / "main.tex").read_text(), "% paper-template\n")
        metadata = json.loads((destination / templates.METADATA_NAME).read_text())
        self.assertEqual(metadata["template"], "prism")
        self.assertEqual(metadata["prism_version"], build_support.project_version())
        self.assertEqual(templates.template_for_project(destination), "prism")
        self.assertEqual(list(destination.parent.glob(".*.prism-init-*")), [])

    def test_ddt_initialization_is_offline_and_copies_shared_examples(self):
        destination = self.root / "论文 with spaces" / "DDT review"
        with mock.patch.object(templates, "nature_package", side_effect=AssertionError("unexpected network package")), mock.patch.object(templates, "bib_package", side_effect=AssertionError("unexpected network package")):
            templates.initialize(destination, False, "ddt")
        self.assertEqual((destination / "main.tex").read_text(), "% ddt-template\n")
        self.assertEqual((destination / "examples.tex").read_text(), "% shared standalone examples\n")
        metadata = json.loads((destination / templates.METADATA_NAME).read_text())
        self.assertEqual(metadata["template"], "ddt")
        self.assertEqual(metadata["engine"], "pdflatex")
        self.assertNotIn("upstream", metadata)
        self.assertEqual(templates.template_for_project(destination), "ddt")
        self.assertFalse(list(destination.glob("*.zip")))

    def test_nature_communications_initialization_is_offline(self):
        destination = self.root / "论文 with spaces" / "Nature Communications"
        with mock.patch.object(templates, "nature_package", side_effect=AssertionError("unexpected network package")), mock.patch.object(templates, "bib_package", side_effect=AssertionError("unexpected network package")):
            templates.initialize(destination, False, "nature-communications")
        self.assertEqual((destination / "main.tex").read_text(), "% nature-communications-template\n")
        self.assertEqual((destination / "examples.tex").read_text(), "% shared standalone examples\n")
        metadata = json.loads((destination / templates.METADATA_NAME).read_text())
        self.assertEqual(metadata["template"], "nature-communications")
        self.assertEqual(metadata["engine"], "pdflatex")
        self.assertNotIn("upstream", metadata)
        self.assertEqual(templates.template_for_project(destination), "nature-communications")
        self.assertFalse(list(destination.glob("*.zip")))

    def test_jcim_initialization_is_offline_and_copies_shared_examples(self):
        destination = self.root / "论文 with spaces" / "JCIM manuscript"
        with mock.patch.object(templates, "nature_package", side_effect=AssertionError("unexpected network package")), mock.patch.object(templates, "bib_package", side_effect=AssertionError("unexpected network package")):
            templates.initialize(destination, False, "jcim")
        self.assertEqual((destination / "main.tex").read_text(), "% jcim-template\n")
        self.assertEqual((destination / "examples.tex").read_text(), "% shared standalone examples\n")
        metadata = json.loads((destination / templates.METADATA_NAME).read_text())
        self.assertEqual(metadata["template"], "jcim")
        self.assertEqual(metadata["engine"], "pdflatex")
        self.assertNotIn("upstream", metadata)
        self.assertEqual(templates.template_for_project(destination), "jcim")
        self.assertFalse(list(destination.glob("*.zip")))

    def science_fixture(self):
        """Use synthetic bytes so tests never redistribute the AAAS files."""
        files = {name: f"synthetic upstream {name}\n".encode() for name in templates.SCIENCE_MEMBERS}
        mock.patch.object(templates, "SCIENCE_SHA256", {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}).start()
        source = self.root / "官方 template source"
        source.mkdir()
        for name, content in files.items():
            (source / name).write_bytes(content)
        return source, files

    def test_science_initialization_accepts_directory_and_zip_with_local_metadata(self):
        source, files = self.science_fixture()
        archive_path = self.root / "science package.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            for name, content in files.items():
                archive.writestr(f"official/{name}", content)
        for label, origin in (("directory", source), ("zip", archive_path)):
            with self.subTest(source=label):
                target = self.root / "论文 with spaces" / label
                templates.initialize(target, False, "science-advances", origin)
                self.assertEqual((target / "main.tex").read_text(), "% science-advances-template\n")
                self.assertEqual((target / "examples.tex").read_text(), "% shared standalone examples\n")
                for source_name, destination_name in templates.SCIENCE_MEMBERS.items():
                    self.assertEqual((target / destination_name).read_bytes(), files[source_name])
                metadata = json.loads((target / templates.METADATA_NAME).read_text())
                self.assertEqual(metadata["template"], "science-advances")
                self.assertEqual(metadata["engine"], "pdflatex")
                self.assertNotIn(str(self.root), json.dumps(metadata))
                self.assertEqual(templates.template_for_project(target), "science-advances")

    def test_science_bad_sources_do_not_modify_target_or_create_backup(self):
        source, files = self.science_fixture()
        target = self.root / "existing science manuscript"
        target.mkdir()
        original = target / "research.tex"
        original.write_bytes(b"private research")
        def check_rejected(origin):
            with self.assertRaises(SystemExit):
                templates.initialize(target, True, "science-advances", origin)
            self.assertEqual(original.read_bytes(), b"private research")
            self.assertFalse(target.with_name(target.name + ".backup").exists())
            self.assertEqual(list(self.root.glob(".*.prism-init-*")), [])
        check_rejected(None)
        (source / "scicite.sty").write_bytes(b"wrong file")
        check_rejected(source)
        (source / "scicite.sty").write_bytes(files["scicite.sty"])
        (source / "sciencemag.bst").unlink()
        check_rejected(source)
        (source / "sciencemag.bst").symlink_to(source / "scicite.sty")
        check_rejected(source)

        bad_zip = self.root / "bad science.zip"
        for unsafe in ("duplicate", "traversal", "symlink", "checksum", "missing"):
            with self.subTest(unsafe=unsafe), zipfile.ZipFile(bad_zip, "w") as archive:
                for name, content in files.items():
                    if unsafe == "missing" and name == "sciencemag.bst":
                        continue
                    if unsafe == "symlink" and name == "scicite.sty":
                        info = zipfile.ZipInfo(name)
                        info.create_system = 3
                        info.external_attr = 0o120777 << 16
                        archive.writestr(info, "somewhere")
                    elif unsafe == "checksum" and name == "scicite.sty":
                        archive.writestr(f"folder/{name}", b"tampered")
                    else:
                        archive.writestr(f"folder/{name}", content)
                if unsafe == "duplicate":
                    archive.writestr("other/scicite.sty", files["scicite.sty"])
                elif unsafe == "traversal":
                    archive.writestr("../escape.txt", "bad")
            check_rejected(bad_zip)
        self.assertFalse((self.root / "escape.txt").exists())
        missing_parent = self.root / "new parent" / "paper"
        with self.assertRaises(SystemExit):
            templates.initialize(missing_parent, False, "science-advances", None)
        self.assertFalse(missing_parent.parent.exists())

    def test_science_force_backs_up_existing_project_only_after_validation(self):
        source, files = self.science_fixture()
        target = self.root / "existing science project"
        target.mkdir()
        (target / "research.tex").write_bytes(b"private research")
        templates.initialize(target, True, "science-advances", source)
        self.assertEqual((target.with_name(target.name + ".backup") / "research.tex").read_bytes(), b"private research")
        self.assertEqual((target / "scicite.sty").read_bytes(), files["scicite.sty"])
        for name, content in files.items():
            self.assertEqual((source / name).read_bytes(), content)

    def test_science_refuses_source_and_target_overlap(self):
        source, files = self.science_fixture()
        for target in (source, source / "new project", source.parent):
            with self.subTest(target=target), self.assertRaises(SystemExit):
                templates.initialize(target, True, "science-advances", source)
            for name, content in files.items():
                self.assertEqual((source / name).read_bytes(), content)
            self.assertFalse(source.with_name(source.name + ".backup").exists())
            self.assertFalse((source / "new project").exists())

    def test_offline_nature_keeps_original_zip_and_copies_only_named_members(self):
        archive = self.package()
        source = self.pinned_source(archive)
        destination = self.root / "nature paper"
        templates.initialize(destination, False, "nature", source)
        self.assertEqual((destination / templates.NATURE_ARCHIVE).read_bytes(), archive)
        self.assertTrue((destination / "sn-jnl.cls").is_file())
        self.assertTrue((destination / "sn-nature.bst").is_file())
        self.assertEqual((destination / "examples.tex").read_text(), "% shared standalone examples\n")
        self.assertFalse((destination / "install.sh").exists())
        self.assertFalse((self.root / "not-extracted.txt").exists())
        self.assertEqual(templates.template_for_project(destination), "nature")
        self.assertEqual(templates.template_engine("nature", "auto"), "pdflatex")
        metadata = json.loads((destination / templates.METADATA_NAME).read_text())
        self.assertEqual(metadata["upstream"]["sha256"], hashlib.sha256(archive).hexdigest())

    def test_download_uses_the_same_pinned_archive_validation(self):
        archive = self.package()
        self.pinned_source(archive)
        with mock.patch.object(templates.urllib.request, "urlopen", return_value=io.BytesIO(archive)) as fetch:
            original, members = templates.nature_package(None)
        self.assertEqual(original, archive)
        self.assertEqual(set(members), {"sn-jnl.cls", "sn-nature.bst"})
        self.assertEqual(fetch.call_args.args[0].full_url, templates.NATURE_URL)

    def test_offline_bib_keeps_official_archive_and_only_required_resources(self):
        archive = self.package(template="bib")
        source = self.pinned_source(archive, "bib")
        destination = self.root / "论文 with spaces" / "BIB manuscript"
        templates.initialize(destination, False, "bib", source)
        self.assertEqual((destination / templates.BIB_ARCHIVE).read_bytes(), archive)
        self.assertEqual((destination / "main.tex").read_text(), "% bib-template\n")
        for member, filename in templates.BIB_MEMBERS.items():
            self.assertEqual((destination / filename).read_text(), f"official fixture {member}")
        self.assertEqual((destination / "examples.tex").read_text(), "% shared standalone examples\n")
        self.assertFalse((destination / "install.sh").exists())
        self.assertFalse((self.root / "not-extracted.txt").exists())
        self.assertEqual(templates.template_for_project(destination), "bib")
        metadata = json.loads((destination / templates.METADATA_NAME).read_text())
        self.assertEqual(metadata["engine"], "pdflatex")
        self.assertEqual(metadata["upstream"], {
            "url": templates.BIB_URL,
            "sha256": hashlib.sha256(archive).hexdigest(),
            "archive": templates.BIB_ARCHIVE,
        })
        self.assertEqual(list(destination.parent.glob(".*.prism-init-*")), [])

    def test_bib_download_uses_the_same_pinned_validation_as_offline_import(self):
        archive = self.package(template="bib")
        self.pinned_source(archive, "bib")
        with mock.patch.object(templates.urllib.request, "urlopen", return_value=io.BytesIO(archive)) as fetch:
            original, members = templates.bib_package(None)
        self.assertEqual(original, archive)
        self.assertEqual(set(members), set(templates.BIB_MEMBERS.values()))
        self.assertEqual(fetch.call_args.args[0].full_url, templates.BIB_URL)

    def test_bad_bib_archives_preserve_existing_project_before_force_backup(self):
        destination = self.root / "existing BIB paper"
        destination.mkdir()
        original = destination / "research.tex"
        original.write_bytes(b"private research")
        source = self.root / "wrong.zip"
        source.write_bytes(b"untrusted bytes")
        with self.assertRaisesRegex(SystemExit, "checksum mismatch"):
            templates.initialize(destination, True, "bib", source)
        member = next(iter(templates.BIB_MEMBERS))
        for archive in (b"not a zip", self.package(template="bib", missing=member), self.package(template="bib", symlink=member)):
            with self.subTest(archive=archive[:20]):
                source = self.pinned_source(archive, "bib")
                with self.assertRaisesRegex(SystemExit, "Invalid BIB template ZIP"):
                    templates.initialize(destination, True, "bib", source)
                self.assertEqual(original.read_bytes(), b"private research")
                self.assertFalse(destination.with_name("existing BIB paper.backup").exists())
        self.assertEqual(list(self.root.glob(".*.prism-init-*")), [])

    def test_invalid_bib_package_does_not_create_target_parent(self):
        source = self.root / "wrong.zip"
        source.write_bytes(b"untrusted bytes")
        destination = self.root / "new parent" / "new paper"
        with self.assertRaisesRegex(SystemExit, "checksum mismatch"):
            templates.initialize(destination, False, "bib", source)
        self.assertFalse(destination.parent.exists())

    def test_bad_hash_or_invalid_zip_leaves_force_target_and_backups_untouched(self):
        destination = self.root / "existing"
        destination.mkdir()
        original = destination / "research.tex"
        original.write_bytes(b"private research")
        source = self.root / "wrong.zip"
        source.write_bytes(b"untrusted bytes")
        with self.assertRaisesRegex(SystemExit, "checksum mismatch"):
            templates.initialize(destination, True, "nature", source)
        self.assertEqual(original.read_bytes(), b"private research")
        self.assertFalse(destination.with_name("existing.backup").exists())
        for archive in (b"not a zip", self.package(missing=next(iter(templates.NATURE_MEMBERS))), self.package(symlink=next(iter(templates.NATURE_MEMBERS)))):
            with self.subTest(archive=archive[:20]):
                source = self.pinned_source(archive)
                with self.assertRaisesRegex(SystemExit, "Invalid Nature template ZIP"):
                    templates.initialize(destination, True, "nature", source)
                self.assertEqual(original.read_bytes(), b"private research")
                self.assertFalse(destination.with_name("existing.backup").exists())
        self.assertEqual(list(self.root.glob(".*.prism-init-*")), [])

    def test_nonempty_file_and_symlink_targets_are_protected(self):
        destination = self.root / "existing"
        destination.mkdir()
        (destination / "original").write_text("keep")
        with self.assertRaisesRegex(SystemExit, "not empty"):
            templates.initialize(destination, False)
        regular_file = self.root / "file"
        regular_file.write_text("keep")
        link = self.root / "link"
        link.symlink_to(destination, target_is_directory=True)
        for target in (regular_file, link):
            with self.subTest(target=target), self.assertRaises(SystemExit):
                templates.initialize(target, True)
        self.assertEqual((destination / "original").read_text(), "keep")
        self.assertEqual(regular_file.read_text(), "keep")
        self.assertTrue(link.is_symlink())

    def test_force_backup_preserves_files_links_and_existing_backup(self):
        destination = self.root / "existing"
        destination.mkdir()
        (destination / "original").write_bytes(b"research")
        (destination / "attachment").symlink_to("original")
        destination.with_name("existing.backup").write_text("older backup")
        templates.initialize(destination, True)
        backup = destination.with_name("existing.backup-1")
        self.assertEqual((backup / "original").read_bytes(), b"research")
        self.assertEqual(os.readlink(backup / "attachment"), "original")
        self.assertEqual(destination.with_name("existing.backup").read_text(), "older backup")
        self.assertTrue((destination / "main.tex").is_file())

    def test_staging_and_publication_failures_restore_existing_target(self):
        destination = self.root / "existing"
        destination.mkdir()
        (destination / "original").write_text("keep")
        for operation in ("copytree", "replace"):
            module = templates.shutil if operation == "copytree" else templates.os
            with self.subTest(operation=operation), mock.patch.object(module, operation, side_effect=OSError("deliberate failure")):
                with self.assertRaisesRegex(SystemExit, "Could not initialize"):
                    templates.initialize(destination, True)
            self.assertEqual((destination / "original").read_text(), "keep")
            self.assertFalse(destination.with_name("existing.backup").exists())
            self.assertEqual(list(self.root.glob(".*.prism-init-*")), [])

    def test_changed_target_is_not_backed_up_or_replaced(self):
        destination = self.root / "existing"
        destination.mkdir()
        original = destination / "original"
        original.write_text("before")
        def changed_source(source):
            original.write_text("changed while downloading")
            return b"archive", {"sn-jnl.cls": b"class", "sn-nature.bst": b"bst"}
        with mock.patch.object(templates, "nature_package", side_effect=changed_source):
            with self.assertRaisesRegex(SystemExit, "changed during preparation"):
                templates.initialize(destination, True, "nature")
        self.assertEqual(original.read_text(), "changed while downloading")
        self.assertFalse(destination.with_name("existing.backup").exists())

    def test_template_metadata_rejects_unknown_or_broken_content(self):
        self.assertIsNone(templates.template_for_project(self.root))
        for content in ('{"template":"unknown"}', '{"template":[]}', "[]", "not json"):
            with self.subTest(content=content):
                (self.root / templates.METADATA_NAME).write_text(content)
                with self.assertRaisesRegex(SystemExit, "Invalid Prism template metadata"):
                    templates.template_for_project(self.root)

    def test_pdflatex_dependencies_do_not_require_unicode_fonts_or_cjk(self):
        def kpsewhich(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, f"/tex/{command[-1]}\n", "")
        with mock.patch.object(build_support.shutil, "which", side_effect=lambda command: f"/bin/{command}"), mock.patch.object(build_support.subprocess, "run", side_effect=kpsewhich):
            ok, rows = build_support.dependency_report("pdflatex", templates.NATURE_PACKAGES)
        self.assertTrue(ok)
        report = "\n".join(rows)
        self.assertIn("engine: pdflatex", report)
        for excluded in ("fontspec", "Fandol", "texgyre", "xeCJK", "luatexja"):
            self.assertNotIn(excluded, report)
        self.assertIn("-pdf", build_support.latexmk_command("pdflatex", "main.tex"))
        with mock.patch.object(build_support.shutil, "which", side_effect=lambda command: "/bin/pdflatex" if command == "pdflatex" else None):
            self.assertEqual(build_support.choose_engine("pdflatex"), "pdflatex")
            with self.assertRaises(SystemExit):
                build_support.choose_engine("auto")

    def test_registered_profiles_reject_incompatible_engines(self):
        self.assertEqual(templates.template_engine("prism", "auto"), "auto")
        self.assertEqual(templates.template_engine("nature", "auto"), "pdflatex")
        self.assertEqual(templates.template_engine("nature", "pdflatex"), "pdflatex")
        self.assertEqual(templates.template_engine("nature-communications", "auto"), "pdflatex")
        self.assertEqual(templates.template_engine("nature-communications", "pdflatex"), "pdflatex")
        self.assertEqual(templates.template_engine("bib", "auto"), "pdflatex")
        self.assertEqual(templates.template_engine("bib", "pdflatex"), "pdflatex")
        self.assertEqual(templates.template_engine("ddt", "auto"), "pdflatex")
        self.assertEqual(templates.template_engine("ddt", "pdflatex"), "pdflatex")
        self.assertEqual(templates.template_engine("jcim", "auto"), "pdflatex")
        self.assertEqual(templates.template_engine("jcim", "pdflatex"), "pdflatex")
        self.assertEqual(templates.template_engine("science-advances", "auto"), "pdflatex")
        self.assertEqual(templates.template_engine("science-advances", "pdflatex"), "pdflatex")
        self.assertEqual(templates.template_engine(None, "pdflatex"), "pdflatex")
        for template, engine in (("prism", "pdflatex"), ("nature", "xelatex"), ("nature", "lualatex"), ("nature-communications", "xelatex"), ("nature-communications", "lualatex"), ("bib", "xelatex"), ("bib", "lualatex"), ("ddt", "xelatex"), ("ddt", "lualatex"), ("jcim", "xelatex"), ("jcim", "lualatex"), ("science-advances", "xelatex"), ("science-advances", "lualatex")):
            with self.subTest(template=template, engine=engine):
                with self.assertRaisesRegex(SystemExit, "requires"):
                    templates.template_engine(template, engine)
                with self.assertRaisesRegex(SystemExit, "requires"):
                    templates.template_packages(template, engine)

    def test_bib_dependency_profile_has_oup_packages_and_local_resources(self):
        packages = templates.template_packages("bib", "auto")
        for package in ("flushend.sty", "totcount.sty", "algorithm.sty", "tikz.sty", "subcaption.sty", "unsrt.bst"):
            self.assertIn(package, packages)
        for excluded in ("fontspec.sty", "unicode-math.sty", "xeCJK.sty"):
            self.assertNotIn(excluded, packages)
        self.assertEqual(templates.template_resources("bib"), ("oup-authoring-template.cls", "oup-plain.bst"))

    def test_nature_communications_dependencies_use_distribution_resources(self):
        packages = templates.template_packages("nature-communications", "auto")
        for package in ("article.cls", "natbib.sty", "unsrt.bst", "graphicx.sty", "longtable.sty"):
            self.assertIn(package, packages)
        for excluded in ("sn-jnl.cls", "fontspec.sty", "unicode-math.sty", "xeCJK.sty"):
            self.assertNotIn(excluded, packages)
        self.assertEqual(templates.template_resources("nature-communications"), ())

    def test_ddt_dependency_profile_uses_tex_distribution_resources(self):
        packages = templates.template_packages("ddt", "auto")
        for package in ("elsarticle.cls", "elsarticle-num.bst", "natbib.sty", "graphicx.sty", "longtable.sty", "subcaption.sty"):
            self.assertIn(package, packages)
        for excluded in ("fontspec.sty", "unicode-math.sty", "xeCJK.sty"):
            self.assertNotIn(excluded, packages)
        self.assertEqual(templates.template_resources("ddt"), ())

    def test_jcim_dependency_profile_uses_acs_package_and_style(self):
        packages = templates.template_packages("jcim", "auto")
        for package in ("achemso.sty", "achemso.bst", "natbib.sty", "natmove.sty", "xkeyval.sty", "graphicx.sty"):
            self.assertIn(package, packages)
        for excluded in ("fontspec.sty", "unicode-math.sty", "xeCJK.sty", "mciteplus.sty"):
            self.assertNotIn(excluded, packages)
        self.assertEqual(templates.template_resources("jcim"), ())

    def test_science_dependencies_use_local_upstream_resources(self):
        packages = templates.template_packages("science-advances", "auto")
        self.assertIn("article.cls", packages)
        self.assertNotIn("fontspec.sty", packages)
        self.assertNotIn("scicite.sty", packages)
        self.assertNotIn("sciencemag.bst", packages)
        self.assertIn("scicite.sty", templates.template_resources("science-advances"))
        self.assertIn("sciencemag.bst", templates.template_resources("science-advances"))


if __name__ == "__main__":
    unittest.main()
