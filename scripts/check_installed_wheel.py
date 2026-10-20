"""Smoke a noneditable tf-build wheel installed outside the source checkout.

Usage: python scripts/check_installed_wheel.py /absolute/path/to/checkout
"""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PUBLIC_APIS = {
    "agora": "prepare_agora_output",
    "feature_docs": "scan_tf_feature_headers",
    "fingerprint": "fingerprint_tree",
    "publication": "publish_path_no_clobber",
    "report": "BuildReport",
    "source": "validate_git_revision",
    "tf_strings": "require_tf_safe_string",
    "validate": "validate_tf_artifact",
    "workspace": "BuildWorkspace",
}



def _check_publication_example(checkout: Path) -> None:
    """Exercise the installed package's actual Text-Fabric publication workflow."""
    from tf.fabric import Fabric

    from tf_build.fingerprint import fingerprint_tree
    from tf_build.validate import FeatureRequirement, validate_tf_artifact

    example = checkout / "examples" / "tiny_tf_publication.py"
    if not example.is_file():
        raise RuntimeError("installed-wheel publication example is missing")

    with tempfile.TemporaryDirectory(prefix="tf-build-installed-e2e-") as directory:
        workspace = Path(directory)
        destination = workspace / "published"
        command = [sys.executable, "-I", str(example), str(destination)]

        def run_example() -> subprocess.CompletedProcess[str]:
            try:
                return subprocess.run(
                    command,
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=120,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("installed-wheel publication example timed out") from exc

        first = run_example()
        if first.returncode != 0:
            raise RuntimeError(
                f"installed-wheel publication example failed with exit {first.returncode}"
            )
        try:
            claimed = json.loads(first.stdout)
        except (ValueError, TypeError) as exc:
            raise RuntimeError("installed-wheel publication returned invalid JSON") from exc

        expected = {
            "otype.tf",
            "oslots.tf",
            "otext.tf",
            "wordText.tf",
            "attestation.tf",
            "run-report.json",
        }
        if not destination.is_dir() or not all(
            (destination / filename).is_file() for filename in expected
        ):
            raise RuntimeError("installed-wheel publication omitted required TF artifacts")

        try:
            report = json.loads(
                (destination / "run-report.json").read_text(encoding="utf-8")
            )
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError("installed-wheel publication report is invalid") from exc
        if report.get("schema") != 1 or report.get("producer", {}).get("name") != (
            "tf-build-tiny-demo"
        ):
            raise RuntimeError("installed-wheel publication report identity mismatch")

        validated = validate_tf_artifact(
            destination,
            level="all",
            require_otext=True,
            required_features=(
                FeatureRequirement("wordText", kind="node", value_type="str"),
                FeatureRequirement(
                    "attestation", kind="edge", value_type="str", edge_values=True
                ),
            ),
        )
        if validated.level != "all":
            raise RuntimeError("installed-wheel publication was not exhaustively reloaded")
        fingerprint = fingerprint_tree(destination)
        if not isinstance(claimed, dict) or (
            claimed.get("algorithm") != fingerprint.algorithm
            or claimed.get("digest") != fingerprint.digest
            or claimed.get("files") != len(fingerprint.files)
        ):
            raise RuntimeError("installed-wheel publication fingerprint mismatch")

        fabric = Fabric(locations=[str(destination)], silent="deep")
        api = fabric.load("wordText attestation", silent="deep")
        if (
            api is None
            or isinstance(api, bool)
            or api.F.wordText.v(1) != "hello"
            or api.F.wordText.v(2) != "world"
            or api.E.attestation.f(3) != {1: "example"}
        ):
            raise RuntimeError("installed-wheel publication Text-Fabric query mismatch")

        refused = run_example()
        if refused.returncode == 0 or "exists" not in refused.stderr.lower():
            raise RuntimeError("installed-wheel publication did not refuse overwrite")
        if fingerprint_tree(destination) != fingerprint:
            raise RuntimeError("installed-wheel publication mutated an existing artifact")

    print("Installed-wheel Text-Fabric publication E2E PASS")

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

    _check_publication_example(root)
    print(f"Installed tf-build {version} from {module_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check_installed_wheel.py ABSOLUTE_CHECKOUT")
    try:
        check_distribution(Path(sys.argv[1]))
    except (RuntimeError, OSError, ImportError) as exc:
        raise SystemExit(f"Wheel smoke failed: {exc}") from exc
