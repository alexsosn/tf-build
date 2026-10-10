"""Runnable example: serialize, reload, fingerprint and publish a tiny real TF corpus.

Usage:
    python examples/tiny_tf_publication.py /tmp/my-new-tf-artifact

The destination must not exist. This is an example of composing primitives,
not a generic converter or an Agora runtime.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from tf.fabric import Fabric  # type: ignore[import-untyped]

from tf_build.fingerprint import fingerprint_tree
from tf_build.report import ArtifactSummary, BuildReport, PhaseTiming, Producer
from tf_build.validate import FeatureRequirement, validate_tf_artifact
from tf_build.workspace import BuildWorkspace


def _save_tiny_corpus(directory: Path) -> None:
    """Emit a minimal word-slot TF graph using the real serializer."""
    fabric = Fabric(locations=[str(directory)], silent="deep")
    saved = fabric.save(
        nodeFeatures={
            "otype": {1: "word", 2: "word", 3: "sentence"},
            "wordText": {1: "hello", 2: "world"},
            "sentenceLabel": {3: "s1"},
        },
        edgeFeatures={
            "oslots": {3: {1, 2}},
            "attestation": {3: {1: "example"}},
        },
        metaData={
            "otype": {"valueType": "str"},
            "oslots": {"valueType": "str"},
            "wordText": {"valueType": "str", "description": "Example word surface"},
            "sentenceLabel": {"valueType": "str"},
            "attestation": {"valueType": "str", "edgeValues": True},
            "otext": {
                "sectionTypes": "sentence",
                "sectionFeatures": "sentenceLabel",
                "fmt:text-orig-full": "{wordText} ",
            },
        },
        silent="deep",
    )
    if not saved:
        raise RuntimeError("Text-Fabric did not save the tiny example corpus")


def publish_tiny_corpus(destination: str | Path) -> dict[str, str | int]:
    """Demonstrate a create-only checked publication with no generic runner API."""
    with BuildWorkspace(destination) as workspace:
        staging = workspace.path
        started = perf_counter()
        _save_tiny_corpus(staging)
        validate_tf_artifact(
            staging,
            level="all",
            require_otext=True,
            required_features=(
                FeatureRequirement("wordText", kind="node", value_type="str"),
                FeatureRequirement(
                    "attestation", kind="edge", value_type="str", edge_values=True
                ),
            ),
        )

        elapsed = perf_counter() - started
        tf_files = [p for p in staging.glob("*.tf") if p.is_file()]
        report = BuildReport(
            producer=Producer("tf-build-tiny-demo", "1.0"),
            phases=(PhaseTiming("materialize", elapsed),),
            artifacts=(
                ArtifactSummary(
                    "tf",
                    files=len(tf_files),
                    bytes=sum(path.stat().st_size for path in tf_files),
                ),
            ),
        )
        (staging / "run-report.json").write_text(report.to_json(), encoding="utf-8")

        before = fingerprint_tree(staging)
        published = workspace.publish()

    after = fingerprint_tree(published)
    if after != before:
        raise RuntimeError("published artifact bytes differ from checked staging")
    return {
        "algorithm": after.algorithm,
        "digest": after.digest,
        "files": len(after.files),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="absent destination directory")
    args = parser.parse_args(argv)
    print(json.dumps(publish_tiny_corpus(args.destination), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
