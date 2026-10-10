"""Smoke a noneditable tf-build wheel installed outside the source checkout.

Usage: python scripts/check_installed_wheel.py /absolute/path/to/checkout
"""

from __future__ import annotations

import importlib
import importlib.metadata
import sys
from pathlib import Path

PUBLIC_APIS = {
    "agora": "prepare_agora_output",
    "feature_docs": "scan_tf_feature_headers",
    "fingerprint": "fingerprint_tree",
    "report": "BuildReport",
    "source": "validate_git_revision",
    "tf_strings": "require_tf_safe_string",
    "validate": "validate_tf_artifact",
    "workspace": "BuildWorkspace",
}


def check_distribution(checkout: Path) -> None:
    """Reject missing, editable or incomplete installed wheels."""
    try:
        version = importlib.metadata.version("tf-build")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("tf-build distribution is not installed") from exc

    root = checkout.resolve(strict=True)
    package = importlib.import_module("tf_build")
    package_file = getattr(package, "__file__", None)
    if package_file is None:
        raise RuntimeError("installed tf-build package has no file")
    module_path = Path(package_file).resolve()
    if module_path.is_relative_to(root):
        raise RuntimeError(f"tf-build imports from editable checkout: {module_path}")

    for name, attr in sorted(PUBLIC_APIS.items()):
        module = importlib.import_module(f"tf_build.{name}")
        module_file = getattr(module, "__file__", None)
        if module_file is None or Path(module_file).resolve().is_relative_to(root):
            raise RuntimeError(f"public module {name} was imported from checkout")
        if not hasattr(module, attr):
            raise RuntimeError(f"missing public API tf_build.{name}.{attr}")

    source = importlib.import_module("tf_build.source")
    strings = importlib.import_module("tf_build.tf_strings")
    assert source.validate_git_revision("A" * 40) == "a" * 40
    assert strings.require_tf_safe_string("line\nvalue", feature="text", node=1) == (
        "line\nvalue"
    )
    try:
        strings.require_tf_safe_string("alpha\rhidden", feature="text", node=1)
    except strings.TFStringSafetyError:
        pass
    else:
        raise RuntimeError("installed wheel lacks U+000D preflight behavior")

    print(f"Installed tf-build {version} from {module_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check_installed_wheel.py ABSOLUTE_CHECKOUT")
    try:
        check_distribution(Path(sys.argv[1]))
    except (RuntimeError, OSError, ImportError) as exc:
        raise SystemExit(f"Wheel smoke failed: {exc}") from exc
