"""End-to-end composition tests with the real Text-Fabric serializer and loader."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from tf.fabric import Fabric  # type: ignore[import-untyped]

from tf_build.fingerprint import fingerprint_tree
from tf_build.validate import ArtifactValidationError, validate_tf_artifact
from tf_build.workspace import BuildWorkspace


def _invoke_example(destination: Path) -> subprocess.CompletedProcess[str]:
    root = Path(__file__).resolve().parents[1]
    return subprocess.run(
        [sys.executable, str(root / "examples" / "tiny_tf_publication.py"), str(destination)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_runnable_example_publishes_real_validated_artifact(
    tmp_path: Path,
) -> None:
    published = tmp_path / "published"
    result = _invoke_example(published)
    assert result.returncode == 0, result.stderr
    stdout = json.loads(result.stdout)

    assert published.is_dir()
    for required in ("otype.tf", "oslots.tf", "otext.tf", "wordText.tf",
                     "attestation.tf", "run-report.json"):
        assert (published / required).is_file()
    report = json.loads((published / "run-report.json").read_text(encoding="utf-8"))
    assert report["schema"] == 1
    assert report["producer"]["name"] == "tf-build-tiny-demo"
    assert len(report["phases"]) == 1
    assert report["phases"][0]["name"] == "materialize"
    assert report["phases"][0]["seconds"] > 0.0
    assert "digest" not in report
    assert "fingerprint" not in report

    actual = fingerprint_tree(published)
    assert stdout["digest"] == actual.digest
    assert stdout["algorithm"] == actual.algorithm
    assert stdout["files"] == len(actual.files)
    assert {"otype.tf", "oslots.tf", "run-report.json"} <= {
        item.path for item in actual.files
    }

    checked = validate_tf_artifact(published, level="all", require_otext=True)
    assert checked.level == "all"
    assert fingerprint_tree(published) == actual


def test_example_refuses_second_publish_without_touching_existing_artifact(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "published"
    initial = _invoke_example(destination)
    assert initial.returncode == 0, initial.stderr
    before = fingerprint_tree(destination)

    refused = _invoke_example(destination)
    assert refused.returncode != 0
    assert "exists" in refused.stderr.lower()
    assert fingerprint_tree(destination) == before


def test_invalid_real_tf_body_aborts_without_publishing(
    tmp_path: Path,
) -> None:
    committed = tmp_path / "already-published"
    committed.mkdir()
    (committed / "sentinel.tf").write_bytes(b"committed bytes")
    sibling_before = fingerprint_tree(committed)
    failed_target = tmp_path / "broken-output"

    with pytest.raises(ArtifactValidationError, match="load"):
        with BuildWorkspace(failed_target) as workspace:
            fabric = Fabric(locations=[str(workspace.path)], silent="deep")
            saved = fabric.save(
                nodeFeatures={
                    "otype": {1: "word", 2: "word", 3: "sentence"},
                    "integer": {1: 12, 2: 13},
                },
                edgeFeatures={"oslots": {3: {1, 2}}},
                metaData={
                    "otype": {"valueType": "str"},
                    "integer": {"valueType": "int"},
                    "oslots": {"valueType": "str"},
                },
                silent="deep",
            )
            assert saved
            integer = workspace.path / "integer.tf"
            header, separator, _ = integer.read_bytes().partition(b"\n\n")
            assert separator
            integer.write_bytes(header + separator + b"1\tINVALID_INTEGER\n")
            validate_tf_artifact(workspace.path, level="all")

    assert not failed_target.exists()
    assert fingerprint_tree(committed) == sibling_before
    assert not list(tmp_path.glob(".broken-output.tf-build-*"))
