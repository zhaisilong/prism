"""Compatibility API for the explicit catalog and project initialization layers.

New integrations can inject TemplateCatalog and AssetContext directly.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from .paths import PROJECT_DIR, ASSET_DIR, METADATA_NAME
from .catalog import (
    CATALOG, TEMPLATES, BUILD_PROFILES, TemplateDefinition, TemplateCatalog, BuildProfile,
    template_choices, resolve_template, article_type_choices, format_template_catalog,
    template_profile, template_isolated_build, template_article_type, template_engine, template_packages,
    PRISM_PACKAGES, NATURE_PACKAGES, NATURE_COMMUNICATIONS_PACKAGES, SCIENCE_PACKAGES,
    BIB_PACKAGES, DDT_PACKAGES, JCIM_PACKAGES, WILEY_PACKAGES, ADVANCED_SCIENCE_PACKAGES,
)
from .project import ProjectConfig, load_project_config
from .template_assets import (
    AssetContext, BUNDLED_PACKAGES, BUNDLED_NOTICES, NATURE_URL, NATURE_SIZE, NATURE_SHA256,
    NATURE_ARCHIVE, NATURE_MEMBERS, BIB_URL, BIB_SIZE, BIB_SHA256, BIB_ARCHIVE, BIB_MEMBERS,
    BIOINFORMATICS_MEMBERS, SCIENCE_SHA256, SCIENCE_MEMBERS,
)
from . import initialization, template_assets


def _asset_context() -> AssetContext:
    return AssetContext(ASSET_DIR, NATURE_SIZE, NATURE_SHA256, BIB_SIZE, BIB_SHA256, SCIENCE_SHA256)


def nature_package(source):
    return template_assets.nature_package(source, context=_asset_context())


def bib_package(source):
    return template_assets.bib_package(source, context=_asset_context())


def bioinformatics_package(source):
    return template_assets.bioinformatics_package(source, context=_asset_context())


def science_package(source):
    return template_assets.science_package(source, context=_asset_context())


def _bundled_package(package_id, required):
    return template_assets._bundled_package(package_id, required, context=_asset_context())


def initialize(target: Path, force: bool, template: str = "prism", source: Path | None = None,
               language: str = "bilingual", article_type: str | None = None) -> int:
    return initialization.initialize(
        target, force, template, source, language, article_type, context=_asset_context(),
        source_readers={"nature": nature_package, "oup-numeric": bib_package,
                        "oup-authoryear": bioinformatics_package, "science": science_package},
    )


def _template_metadata(project):
    config = load_project_config(project)
    return config.template, config.variant, config.language, config.article_type


def template_for_project(project):
    return load_project_config(project).template


def template_variant_for_project(project):
    return load_project_config(project).variant


def template_language_for_project(project):
    return load_project_config(project).language


def template_article_type_for_project(project):
    return load_project_config(project).article_type


def template_resources(
    template: str | None, variant: str | None = None, language: str | None = None,
) -> tuple[str, ...]:
    """Project-local upstream resources required by an initialized template."""
    sources = {
        "nature": NATURE_MEMBERS, "oup-numeric": BIB_MEMBERS,
        "oup-authoryear": BIOINFORMATICS_MEMBERS, "science": SCIENCE_MEMBERS,
    }
    source = template_profile(template, variant)["source"] if template else None
    resources = () if source == "nature" and variant != "sn-jnl" else (
        tuple(sources[source].values()) if source else ()
    )
    if template and language == "bilingual":
        resources += ("prism-cjk.sty",)
    if template:
        resources += template_profile(template, variant).get("resources", ())
    return resources
