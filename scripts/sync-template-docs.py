#!/usr/bin/env python3
"""Check or explicitly regenerate the catalog/count blocks in public guides."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True  # --check must not create repository caches.
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from prism_latex.catalog import CATALOG


ROOT = Path(__file__).resolve().parents[1]


def ordered_templates(catalog):
    return sorted(catalog.templates.values(),
                  key=lambda item: (item.publisher is None, (item.publisher or "").casefold(),
                                    item.venue.casefold(), item.alias))


def article_types(item) -> str:
    if not item.article_types:
        return f"`{item.article_type}`"
    return "、".join(f"`{kind}`" + ("（默认）" if kind == item.article_type else "")
                    for kind in item.article_types)


def generated_blocks(catalog):
    """Generate declarations only; submission guidance remains hand maintained."""
    templates = ordered_templates(catalog)
    groups = {}
    for item in templates:
        groups.setdefault(item.publisher or "通用", []).append(item)
    summary = ["| 出版社 / 类别 | 模板短名称 |", "| --- | --- |"]
    for publisher, items in groups.items():
        summary.append(f"| {publisher} | " + "、".join(
            f"[`{item.alias}`]({item.guide_path})" for item in items) + " |")
    guide = ["| 模板 | 期刊 / 用途 |", "| --- | --- |"]
    overview = ["| 标识 | 期刊 / 用途 | 出版社 | 稿型 |", "| --- | --- | --- | --- |"]
    for item in templates:
        path = Path(item.guide_path).relative_to("docs").as_posix()
        guide.append(f"| [`{item.alias}`]({path}) | {item.venue} |")
        overview.append(f"| [`{item.alias}`]({path}) | {item.venue} | "
                        f"{item.publisher or '通用'} | {article_types(item)} |")
    return {
        "README.md": {
            "template-count": f"- **{len(templates)} 套离线模板**：覆盖化学、生物信息学与综合期刊，按出版社分组查询；可选稿型由目录统一列出，模板资源随仓库提供。",
            "template-catalog": "\n".join(summary),
        },
        "docs/guide.zh-CN.md": {"template-catalog": "\n".join(guide)},
        "docs/templates.md": {"template-catalog": "\n".join(overview)},
    }


def replace_block(text: str, name: str, body: str) -> str:
    start, end = f"<!-- prism:{name}:start -->", f"<!-- prism:{name}:end -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"Expected one start/end marker for {name}.")
    pattern = re.compile(re.escape(start) + r"\n.*?\n?" + re.escape(end), re.S)
    result, count = pattern.subn(lambda _: start + "\n" + body + "\n" + end, text)
    if count != 1:
        raise ValueError(f"Invalid marker order for {name}.")
    return result


def synchronize(repository: Path = ROOT, *, write: bool = False, catalog=CATALOG):
    """Return relative paths with drift; validate every marker before writing."""
    changes = {}
    for relative, blocks in generated_blocks(catalog).items():
        path = repository / relative
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError("Documentation paths must not contain symbolic links.")
        original = path.read_text(encoding="utf-8")
        updated = original
        for name, body in blocks.items():
            updated = replace_block(updated, name, body)
        if updated != original:
            changes[relative] = updated
    if write:
        for relative, content in changes.items():
            (repository / relative).write_text(content, encoding="utf-8")
    return tuple(changes)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Report drift without changing files (default)")
    mode.add_argument("--write", action="store_true", help="Regenerate only the marked catalog/count blocks")
    args = parser.parse_args(argv)
    try:
        changed = synchronize(write=args.write)
    except (OSError, ValueError) as exc:
        print(f"Could not synchronize template docs: {exc}", file=sys.stderr)
        return 1
    if changed:
        print(("Updated: " if args.write else "Template documentation drift: ") + ", ".join(changed))
        return 0 if args.write else 1
    print("Template documentation is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
