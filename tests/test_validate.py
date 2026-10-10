"""Integration tests against real Text-Fabric artifacts, not a fabricated loader."""

from __future__ import annotations

import os
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


def test_revalidation_ignores_compiled_cache_and_other_tf_directories(
    tmp_path: Path,
) -> None:
    directory = _dataset(tmp_path)
    first = validate_tf_artifact(directory, level="selected")
    assert first.level == "selected"
    # Text-Fabric may create .tf/ caches during load; an extra suffix-matching
    # directory is also not a regular TF feature file.
    (directory / ".tf").mkdir(exist_ok=True)
    (directory / "scratch.tf").mkdir()
    second = validate_tf_artifact(directory, level="all")
    assert second.level == "all"
    assert ".tf" not in second.feature_names
    assert "scratch" not in second.feature_names



@pytest.mark.parametrize("bad_header", ["@valueType=garbage", "@valueType="])
def test_metadata_rejects_invalid_declared_value_type(
    tmp_path: Path, bad_header: str
) -> None:
    directory = _dataset(tmp_path)
    feature = directory / "count.tf"
    text = feature.read_text(encoding="utf-8")
    assert "@valueType=int" in text
    feature.write_text(text.replace("@valueType=int", bad_header), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="count"):
        validate_tf_artifact(directory, level="metadata")


def test_metadata_rejects_edge_values_on_node_feature(tmp_path: Path) -> None:
    directory = _dataset(tmp_path)
    feature = directory / "text.tf"
    text = feature.read_text(encoding="utf-8")
    assert "@node" in text
    feature.write_text(
        text.replace("@node\n", "@node\n@edgeValues\n", 1),
        encoding="utf-8",
    )
    with pytest.raises(ArtifactValidationError, match="text"):
        validate_tf_artifact(directory, level="metadata")


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



@pytest.mark.parametrize("level", ["selected", "all"])
def test_cached_binary_never_masks_corrupted_same_mtime_raw_tf(
    tmp_path: Path, level: ValidationLevel
) -> None:
    directory = _dataset(tmp_path)
    first = validate_tf_artifact(directory, level="all", require_otext=True)
    assert first.level == "all"
    cached = tuple((directory / ".tf").rglob("count.tfx"))
    assert cached, "real Text-Fabric exhaustive load must compile a binary count cache"
    cached_bytes = {p: p.read_bytes() for p in cached}
    before = (directory / "count.tf").stat()

    _corrupt_feature_body(directory / "count.tf")
    os.utime(
        directory / "count.tf",
        ns=(before.st_atime_ns, before.st_mtime_ns),
    )
    assert min(p.stat().st_mtime_ns for p in cached) >= (
        directory / "count.tf"
    ).stat().st_mtime_ns

    declared = validate_tf_artifact(
        directory,
        level="metadata",
        required_features=(FeatureRequirement("count", kind="node", value_type="int"),),
    )
    assert declared.level == "metadata"

    with pytest.raises(ArtifactValidationError, match="load"):
        validate_tf_artifact(
            directory,
            level=level,
            required_features=(FeatureRequirement("count", kind="node"),),
        )

    assert {p: p.read_bytes() for p in cached} == cached_bytes
    assert not tuple(tmp_path.glob(".tf-build-source-verify-*"))


def test_valid_source_load_does_not_rewrite_caller_compiled_cache(
    tmp_path: Path,
) -> None:
    directory = _dataset(tmp_path)
    before_source = {
        p.name: p.read_bytes() for p in directory.glob("*.tf") if p.is_file()
    }
    validate_tf_artifact(directory, level="all")
    original_cache = {
        str(p.relative_to(directory)): p.read_bytes()
        for p in (directory / ".tf").rglob("*.tfx")
    }
    validate_tf_artifact(directory, level="all")
    assert original_cache == {
        str(p.relative_to(directory)): p.read_bytes()
        for p in (directory / ".tf").rglob("*.tfx")
    }
    assert before_source == {
        p.name: p.read_bytes() for p in directory.glob("*.tf") if p.is_file()
    }
    assert not tuple(tmp_path.glob(".tf-build-source-verify-*"))


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
