"""Command-line inspection of emitted native Text-Fabric artifacts.

The library remains composable: this entry point only exposes the existing
artifact validator and does not parse source corpora or infer scholarly meaning.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .validate import ArtifactValidationError, validate_tf_artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tf_build",
        description="Inspect an emitted native Text-Fabric artifact.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser(
        "validate",
        help="validate TF file metadata and optionally reload all feature bodies",
    )
    inspect.add_argument("artifact", type=Path, help="directory containing emitted .tf files")
    inspect.add_argument(
        "--level",
        choices=("metadata", "selected", "all"),
        default="all",
        help="metadata=headers only; selected=warp; all=every feature (default: all)",
    )
    inspect.add_argument(
        "--require-otext",
        action="store_true",
        help="fail if the optional otext.tf configuration is absent",
    )

    args = parser.parse_args(argv)
    try:
        result = validate_tf_artifact(
            args.artifact,
            level=args.level,
            require_otext=args.require_otext,
        )
    except ArtifactValidationError as exc:
        print(f"tf-build: validation failed: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "level": result.level,
                "feature_names": list(result.feature_names),
                "required_features": list(result.required_features),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
