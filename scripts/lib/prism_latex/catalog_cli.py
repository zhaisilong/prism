"""Query and validate the explicit offline template catalog."""

from __future__ import annotations

import argparse
import json
import sys

from .build_support import project_version
from .catalog import CATALOG
from .templates import format_template_catalog


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--version", action="version", version=f"Prism {project_version()}")
    action = result.add_mutually_exclusive_group()
    action.add_argument("--show", metavar="TEMPLATE", help="Show a template alias or stable ID")
    action.add_argument("--validate", action="store_true", help="Validate all definitions and bundled resources offline")
    result.add_argument("--json", action="store_true", help="Emit versioned JSON with --show")
    result.add_argument("--group-by", choices=("none", "publisher"), help="List grouping (default: publisher)")
    return result


def main(argv=None):
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if args.json and not args.show:
        argument_parser.error("--json requires --show TEMPLATE.")
    if args.group_by is not None and (args.show or args.validate):
        argument_parser.error("--group-by applies only to the template list.")
    if args.validate:
        issues = CATALOG.validate()
        if issues:
            print("Template validation failed:\n" + "\n".join(issues), file=sys.stderr)
            return 1
        print(f"Validated {len(CATALOG.templates)} templates and all bundled content profiles (offline).")
        return 0
    if args.show:
        try:
            detail = CATALOG.detail(args.show)
        except ValueError as exc:
            argument_parser.error(str(exc))
        if args.json:
            print(json.dumps(detail, ensure_ascii=False, indent=2))
        else:
            print(f"{detail['venue']} ({detail['alias']})\nID: {detail['id']}")
            print(f"Publisher: {detail['publisher'] or 'Prism'}")
            print("Article types: " + ", ".join(detail["article_types"]) + f" (default: {detail['default_article_type']})")
            for language, policy in detail["languages"].items():
                print(f"{language}: {', '.join(policy['engines'])}; default: {policy['default_engine']}")
            print("Starter documents:")
            for document in detail["documents"]:
                mode = "standalone" if document["standalone"] else "included in main document"
                print(f"  {document['role']}: {document['path']} ({mode})")
            print("Guide: " + detail["guide_path"])
            print("Assets: " + detail["asset_path"])
            for source in detail["sources"]:
                print(f"Source ({source['label']}): {source['url']}")
            print("Article-type selection: " + ("yes" if detail["capabilities"]["article_type_selection"] else "no"))
            print("Official package import: " + ("yes" if detail["capabilities"]["official_package_import"] else "no"))
        return 0
    print(format_template_catalog(args.group_by or "publisher"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
