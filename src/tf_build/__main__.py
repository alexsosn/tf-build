"""Command-line inspection of emitted native Text-Fabric artifacts.

The library remains composable: this entry point only exposes the existing
artifact validator and does not parse source corpora or infer scholarly meaning.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

from .validate import ArtifactValidationError, validate_tf_artifact


class _TFDiagnosticTail(io.TextIOBase):
    """Retain a bounded tail of upstream TF console output for failure reports."""

    _LIMIT = 2048

    def __init__(self) -> None:
        self.tail = ""

    def write(self, message: str) -> int:
        self.tail = (self.tail + message[-self._LIMIT :])[-self._LIMIT :]
        return len(message)


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
    diagnostics = _TFDiagnosticTail()
    try:
        # TF may print decoder errors to stdout and return an unsuccessful load.
        # Capture only a short tail so success stdout remains JSON-only.
        with redirect_stdout(diagnostics):
            result = validate_tf_artifact(
                args.artifact,
                level=args.level,
                require_otext=args.require_otext,
            )
    except ArtifactValidationError as exc:
        print(f"tf-build: validation failed: {exc}", file=sys.stderr)
        if details := diagnostics.tail.strip():
            print(f"tf-build: Text-Fabric diagnostic: {details}", file=sys.stderr)
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
