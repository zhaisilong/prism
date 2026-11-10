"""Validated immutable catalog records, independent of the maintained registry."""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import PurePosixPath
from types import MappingProxyType


class Record(Mapping):
    """Read-only mapping view for existing callers of the registry."""
    def __getitem__(self, key):
        if key not in self:
            raise KeyError(key)
        return getattr(self, key)

    def __iter__(self):
        return (field.name for field in fields(self))

    def __len__(self):
        return len(fields(self))

    def __contains__(self, key):
        return isinstance(key, str) and any(field.name == key for field in fields(self))


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Expected a nonempty repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") or ":" in part for part in value.split("/")):
        raise ValueError("Unsafe repository-relative path")
    return value


@dataclass(frozen=True)
class DocumentRole:
    role: str
    path: str
    standalone: bool = True

    def __post_init__(self):
        relative_path(self.path)
        if not isinstance(self.role, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", self.role) or type(self.standalone) is not bool:
            raise ValueError("Invalid document role")


@dataclass(frozen=True)
class SourceReference:
    label: str
    url: str

    def __post_init__(self):
        if not isinstance(self.label, str) or not self.label or not isinstance(self.url, str) or not self.url.startswith("https://"):
            raise ValueError("Invalid source reference")


@dataclass(frozen=True)
class TemplateDefinition(Record):
    alias: str
    id: str
    kind: str
    venue: str
    publisher: str | None
    article_type: str
    backend: str
    directory: str
    engine: str
    description: str
    article_types: tuple[str, ...] = ()
    guide_path: str = ""
    documents: tuple[DocumentRole, ...] = ()
    sources: tuple[SourceReference, ...] = ()
    required_assets: tuple[str, ...] = ()
    # Reserved identity fields for explicitly registered conference editions.
    edition: int | None = None
    track: str | None = None
    stage: str | None = None

    def __post_init__(self):
        if not isinstance(self.id, str) or self.kind not in ("generic", "family", "journal", "conference") or not self.id.startswith(self.kind + "/"):
            raise ValueError("Invalid Prism template ID or kind")
        if not isinstance(self.alias, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", self.alias):
            raise ValueError("Invalid Prism template alias")
        if any(not isinstance(value, str) or not value for value in (self.id, self.venue, self.article_type, self.backend, self.description)):
            raise ValueError("Invalid template text field")
        if self.publisher is not None and (not isinstance(self.publisher, str) or not self.publisher):
            raise ValueError("Invalid template publisher")
        if any(not re.fullmatch(r"[a-z][a-z0-9-]*", value) for value in (self.article_type, self.backend)):
            raise ValueError("Invalid default article type or build profile identifier")
        if self.edition is not None and (type(self.edition) is not int or self.edition < 1):
            raise ValueError("Invalid conference edition")
        for value in (self.track, self.stage):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError("Invalid conference track or stage")
        relative_path(self.id)
        relative_path(self.directory)
        relative_path(self.guide_path)
        if self.engine not in ("auto", "pdflatex"):
            raise ValueError("Invalid template engine policy")
        if (not isinstance(self.article_types, tuple) or any(not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", value) for value in self.article_types)
                or len(set(self.article_types)) != len(self.article_types)
                or self.article_types and self.article_type not in self.article_types):
            raise ValueError("Invalid article types")
        if not isinstance(self.documents, tuple) or not self.documents or any(not isinstance(role, DocumentRole) for role in self.documents):
            raise ValueError("Invalid template document roles")
        if len({role.role for role in self.documents}) != len(self.documents):
            raise ValueError("Duplicate template document role")
        if not isinstance(self.required_assets, tuple):
            raise ValueError("Invalid starter resources")
        for name in self.required_assets:
            relative_path(name)
        if not isinstance(self.sources, tuple) or any(not isinstance(source, SourceReference) for source in self.sources):
            raise ValueError("Invalid template sources")

    @property
    def supports_article_type(self):
        return bool(self.article_types)


@dataclass(frozen=True)
class BuildProfile(Record):
    packages: tuple[str, ...]
    source: str | None
    examples: bool
    resources: tuple[str, ...] = ()
    required_common: tuple[str, ...] = ()
    shared_assets: tuple[str, ...] = ()
    bundled: tuple[str, Mapping[str, str]] | None = None
    isolate_cwd: bool = False
    xelatex_packages: tuple[str, ...] = ()
    pdftex_packages: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("packages", "resources", "required_common", "shared_assets", "xelatex_packages", "pdftex_packages"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or any(not isinstance(value, str) or not value for value in values):
                raise ValueError("Invalid build profile " + name)
        for name in (*self.resources, *self.required_common, *self.shared_assets):
            relative_path(name)
        if self.source not in (None, "nature", "oup-numeric", "oup-authoryear", "science") or type(self.examples) is not bool or type(self.isolate_cwd) is not bool:
            raise ValueError("Invalid build profile policy")
        if self.bundled is not None:
            if not isinstance(self.bundled, tuple) or len(self.bundled) != 2 or not isinstance(self.bundled[0], str) or not isinstance(self.bundled[1], Mapping):
                raise ValueError("Invalid bundled selection")
            for source, destination in self.bundled[1].items():
                relative_path(source)
                relative_path(destination)
            object.__setattr__(self, "bundled", (self.bundled[0], MappingProxyType(dict(self.bundled[1]))))
