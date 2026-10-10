"""Integration tests against real Text-Fabric artifacts, not a fabricated loader."""

from __future__ import annotations

from pathlib import Path

import pytest
from tf.fabric import Fabric  # type: ignore[import-untyped]

from tf_build.validate import (
    ArtifactValidationError,
    FeatureRequirement,
    ValidationLevel,
    validate_tf_artifact,
)


def _dataset(tmp_path: Path) -> Path:
    directory = tmp_path / "artifact"
    directory.mkdir(parents=True)
    fabric = Fabric(locations=[str(directory)], silent="deep")
    saved = fabric.save(
        nodeFeatures={
            "otype": {1: "word", 2: "word", 3: "sentence"},
            "text": {1: "alpha", 2: "beta"},
            "count": {1: 12, 2: 13},
            "label": {3: "s1"},
        },
        edgeFeatures={
            "oslots": {3: {1, 2}},
            "link": {3: {1}},
            "relation": {3: {1: "attested"}},
        },
        metaData={
            "otype": {"valueType": "str"},
            "oslots": {"valueType": "str"},
            "text": {"valueType": "str"},
            "count": {"valueType": "int"},
            "label": {"valueType": "str"},
            "link": {"valueType": "str"},
            "relation": {"valueType": "str", "edgeValues": True},
            "otext": {
                "sectionTypes": "sentence",
                "sectionFeatures": "label",
                "fmt:text-orig-full": "{text} ",
            },
        },
        silent="deep",
    )
    assert saved, "synthetic Text-Fabric fixture must be written successfully"
    return directory


def _corrupt_feature_body(path: Path) -> None:
    original = path.read_bytes()
    assert b"\n\n" in original
    header = original.split(b"\n\n", 1)[0]
    path.write_bytes(header + b"\n\n1\tINVALID_INTEGER\n")


@pytest.mark.parametrize("level", ["metadata", "selected", "all"])
def test_validation_levels_use_real_tf_artifact(tmp_path: Path, level: ValidationLevel) -> None:
    directory = _dataset(tmp_path)
    result = validate_tf_artifact(
        directory,
        level=level,
        require_otext=True,
        required_features=(
            FeatureRequirement("text", kind="node", value_type="str"),
            FeatureRequirement("count", kind="node", value_type="int"),
            FeatureRequirement("link", kind="edge", edge_values=False),
            FeatureRequirement("relation", kind="edge", edge_values=True),
            FeatureRequirement("otext", kind="config"),
        ),
    )
    assert result.level == level
    assert {"otype", "oslots", "text", "count", "otext", "relation"} <= set(
        result.feature_names
    )
    assert "count" in result.required_features


def test_validation_does_not_change_source_tf_bytes(tmp_path: Path) -> None:
    directory = _dataset(tmp_path)
    before = {p.name: p.read_bytes() for p in directory.glob("*.tf") if p.is_file()}
    checked = validate_tf_artifact(directory, level="all")
    after = {p.name: p.read_bytes() for p in directory.glob("*.tf") if p.is_file()}
    assert checked.level == "all"
    assert after == before


def test_missing_or_incorrect_required_features_are_rejected(tmp_path: Path) -> None:
    directory = _dataset(tmp_path)
    cases = (
        (FeatureRequirement("absent"), "absent"),
        (FeatureRequirement("count", kind="edge"), "count"),
        (FeatureRequirement("count", value_type="str"), "count"),
        (FeatureRequirement("relation", kind="edge", edge_values=False), "relation"),
        (FeatureRequirement("link", kind="edge", edge_values=True), "link"),
        (FeatureRequirement("text", kind="config"), "text"),
    )
    for requirement, match in cases:
        with pytest.raises(ArtifactValidationError, match=match):
            validate_tf_artifact(
                directory, level="metadata", required_features=(requirement,)
            )


def test_missing_warp_and_required_otext_fail_closed(tmp_path: Path) -> None:
    missing = _dataset(tmp_path)
    (missing / "oslots.tf").unlink()
    with pytest.raises(ArtifactValidationError, match="oslots"):
        validate_tf_artifact(missing)

    other = _dataset(tmp_path / "second")
    (other / "otext.tf").unlink()
    with pytest.raises(ArtifactValidationError, match="otext"):
        validate_tf_artifact(other, require_otext=True)


def test_selected_load_detects_corrupted_required_feature(tmp_path: Path) -> None:
    directory = _dataset(tmp_path)
    _corrupt_feature_body(directory / "count.tf")
    requirement = FeatureRequirement("count", kind="node", value_type="int")

    scanned = validate_tf_artifact(
        directory, level="metadata", required_features=(requirement,)
    )
    assert scanned.level == "metadata"
    with pytest.raises(ArtifactValidationError, match="load"):
        validate_tf_artifact(
            directory, level="selected", required_features=(requirement,)
        )


def test_exhaustive_load_detects_corrupt_unselected_feature(tmp_path: Path) -> None:
    directory = _dataset(tmp_path)
    _corrupt_feature_body(directory / "count.tf")

    selected = validate_tf_artifact(
        directory,
        level="selected",
        required_features=(FeatureRequirement("text", kind="node"),),
    )
    assert selected.level == "selected"
    with pytest.raises(ArtifactValidationError, match="load"):
        validate_tf_artifact(directory, level="all")


def test_symlink_artifact_and_tf_feature_are_rejected(tmp_path: Path) -> None:
    directory = _dataset(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(directory, target_is_directory=True)
    with pytest.raises(ArtifactValidationError, match="symlink"):
        validate_tf_artifact(alias)

    target = tmp_path / "target.tf"
    target.write_bytes((directory / "text.tf").read_bytes())
    (directory / "text.tf").unlink()
    (directory / "text.tf").symlink_to(target)
    with pytest.raises(ArtifactValidationError, match="symlink"):
        validate_tf_artifact(directory)


def test_duplicate_requirements_and_invalid_level_fail(tmp_path: Path) -> None:
    directory = _dataset(tmp_path)
    with pytest.raises(ArtifactValidationError, match="duplicate"):
        validate_tf_artifact(
            directory,
            required_features=(FeatureRequirement("text"), FeatureRequirement("text")),
        )
    with pytest.raises(ArtifactValidationError, match="level"):
        validate_tf_artifact(directory, level="unknown")  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["", ".", "..", "a/b", "a\\b", "a b"])
def test_invalid_feature_requirement_name_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="feature name"):
        FeatureRequirement(name)


def test_node_cannot_declare_edge_values_requirement() -> None:
    with pytest.raises(ValueError, match="edge_values"):
        FeatureRequirement("text", kind="node", edge_values=True)
