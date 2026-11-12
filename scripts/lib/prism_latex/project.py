"""Read schema-1 project metadata once and preserve legacy defaults."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from .catalog import CATALOG, LEGACY_NATURE_ID, TemplateCatalog
from .paths import METADATA_NAME


@dataclass(frozen=True)
class ProjectConfig:
    template: str | None = None
    variant: str | None = None
    language: str | None = None
    article_type: str | None = None


def load_project_config(project: Path, *, catalog: TemplateCatalog = CATALOG) -> ProjectConfig:
    path = project / METADATA_NAME
    if not path.exists():
        return ProjectConfig()
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        template = catalog.resolve(metadata["template"])
        if "schema_version" in metadata or "template_id" in metadata:
            if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1:
                raise ValueError("unsupported template metadata schema version")
            expected_id = catalog.templates[template].id
            accepted_ids = {expected_id}
            if template == "nature" and expected_id == "journal/nature":
                accepted_ids.add(LEGACY_NATURE_ID)
            if metadata.get("template_id") not in accepted_ids:
                raise ValueError("template and template_id do not match")
        if "variant" in metadata:
            variant = metadata["variant"]
            if template != "nature" or not isinstance(variant, str) or variant not in ("prism-article", "sn-jnl"):
                raise ValueError("invalid template variant")
        else:
            # Nature projects created before offline starters use sn-jnl.
            variant = "sn-jnl" if template == "nature" else None
        language = metadata.get("language")
        if "language" in metadata and language not in ("bilingual", "english"):
            raise ValueError("invalid template language")
        if "article_type" in metadata and metadata["article_type"] is None:
            raise ValueError("invalid article type")
        article_type = catalog.article_type(template, metadata.get("article_type"))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(f"Invalid Prism template metadata: {path}: {exc}") from exc
    return ProjectConfig(template, variant, language, article_type)
