from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tf.convert.walker import CV  # type: ignore[import-untyped]
from tf.fabric import Fabric  # type: ignore[import-untyped]

import tf_build.validation as validation_module
from tf_build.validation import (
    FeatureRequirement,
    TFArtifactContract,
    TFValidationError,
    validate_tf_artifact,
)


def _build_tiny_tf(path: Path) -> Path:
    path.mkdir()
    fabric = Fabric(locations=str(path), silent="deep")
    cv = CV(fabric, silent="deep")

    def director(builder: Any) -> None:
        document = builder.node("document")
        builder.feature(document, docid="D1")

        first = builder.slot()
        builder.feature(first, text="alpha", rank=1, extra=7)

        second = builder.slot()
        builder.feature(second, text="beta", rank=2, extra=8)

        builder.edge(first, second, link=None, labelled="next")
        builder.terminate(document)

    good = cv.walk(
        director,
        "word",
        otext={
            "sectionTypes": "document",
            "sectionFeatures": "docid",
            "fmt:text-orig-full": "{text} ",
        },
        generic={"name": "tf-build validation fixture", "version": "1"},
        intFeatures={"rank", "extra"},
        featureMeta={},
        warn=True,
    )
    assert good is True
    fabric.clearCache()
    return path


def _contract() -> TFArtifactContract:
    return TFArtifactContract(
        features=(
            FeatureRequirement("text", "node", value_type="str"),
            FeatureRequirement("rank", "node", value_type="int"),
            FeatureRequirement("link", "edge", edge_values=False),
            FeatureRequirement("labelled", "edge", edge_values=True),
        ),
        text_formats=("text-orig-full",),
        section_types=("document",),
        section_features=("docid",),
    )


def _feature_bytes(path: Path) -> dict[str, bytes]:
    return {feature.name: feature.read_bytes() for feature in sorted(path.glob("*.tf"))}


def _corrupt_int_body(path: Path) -> None:
    raw = path.read_bytes()
    header, separator, _body = raw.partition(b"\n\n")
    assert separator == b"\n\n"
    assert b"@valueType=int" in header
    path.write_bytes(header + separator + b"not-an-int\n")


def test_selective_validation_uses_real_tf_and_preserves_feature_bytes(
    tmp_path: Path,
) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")
    before = _feature_bytes(artifact)

    result = validate_tf_artifact(artifact, contract=_contract())

    assert result.mode == "selective"
    assert {"otype", "text", "rank", "extra", "docid"} <= set(result.node_features)
    assert {"oslots", "link", "labelled"} <= set(result.edge_features)
    assert "text-orig-full" in result.text_formats
    assert result.section_types == ("document",)
    assert result.section_features == ("docid",)
    assert _feature_bytes(artifact) == before
    assert not list(artifact.rglob("*.tfx"))


def test_exhaustive_validation_loads_every_discovered_feature(tmp_path: Path) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")

    result = validate_tf_artifact(
        artifact,
        contract=_contract(),
        mode="exhaustive",
    )

    assert result.mode == "exhaustive"
    assert "extra" in result.node_features
    assert not list(artifact.rglob("*.tfx"))


@pytest.mark.parametrize("warp", ["otype.tf", "oslots.tf"])
def test_validation_rejects_missing_mandatory_warp_file(
    tmp_path: Path,
    warp: str,
) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")
    (artifact / warp).unlink()

    with pytest.raises(TFValidationError, match=warp):
        validate_tf_artifact(artifact)


def test_validation_rejects_symlinked_feature(tmp_path: Path) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")
    feature = artifact / "text.tf"
    target = tmp_path / "outside-text.tf"
    feature.replace(target)
    try:
        feature.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable")

    with pytest.raises(TFValidationError, match="symlink"):
        validate_tf_artifact(
            artifact,
            contract=TFArtifactContract(
                features=(FeatureRequirement("text", "node"),)
            ),
        )

    assert target.is_file()


def test_validation_rejects_missing_required_feature(tmp_path: Path) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")

    with pytest.raises(TFValidationError, match="missing_feature"):
        validate_tf_artifact(
            artifact,
            contract=TFArtifactContract(
                features=(FeatureRequirement("missing_feature", "node"),)
            ),
        )


@pytest.mark.parametrize(
    "requirement",
    [
        FeatureRequirement("text", "edge"),
        FeatureRequirement("rank", "node", value_type="str"),
        FeatureRequirement("link", "edge", edge_values=True),
        FeatureRequirement("labelled", "edge", edge_values=False),
    ],
)
def test_validation_rejects_feature_contract_mismatch(
    tmp_path: Path,
    requirement: FeatureRequirement,
) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")

    with pytest.raises(TFValidationError, match=requirement.name):
        validate_tf_artifact(
            artifact,
            contract=TFArtifactContract(features=(requirement,)),
        )


def test_validation_rejects_missing_required_text_format(tmp_path: Path) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")

    with pytest.raises(TFValidationError, match="text-missing"):
        validate_tf_artifact(
            artifact,
            contract=TFArtifactContract(text_formats=("text-missing",)),
        )


def test_validation_rejects_section_contract_mismatch(tmp_path: Path) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")

    with pytest.raises(TFValidationError, match="section"):
        validate_tf_artifact(
            artifact,
            contract=TFArtifactContract(
                section_types=("document",),
                section_features=("wrong_section_feature",),
            ),
        )


def test_selective_validation_rejects_corrupt_required_feature_and_cleans_cache(
    tmp_path: Path,
) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")
    _corrupt_int_body(artifact / "rank.tf")

    with pytest.raises(TFValidationError, match="load"):
        validate_tf_artifact(
            artifact,
            contract=TFArtifactContract(
                features=(FeatureRequirement("rank", "node", value_type="int"),)
            ),
        )

    assert not list(artifact.rglob("*.tfx"))


def test_exhaustive_validation_catches_corrupt_unrequired_feature(
    tmp_path: Path,
) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")
    _corrupt_int_body(artifact / "extra.tf")
    contract = TFArtifactContract(
        features=(FeatureRequirement("text", "node", value_type="str"),)
    )

    selective = validate_tf_artifact(artifact, contract=contract)
    assert selective.mode == "selective"

    with pytest.raises(TFValidationError, match="exhaustive"):
        validate_tf_artifact(artifact, contract=contract, mode="exhaustive")

    assert not list(artifact.rglob("*.tfx"))


def test_contract_rejects_invalid_feature_name() -> None:
    with pytest.raises(ValueError, match="feature name"):
        FeatureRequirement("../lemma", "node")


def test_contract_rejects_edge_values_on_node_requirement() -> None:
    with pytest.raises(ValueError, match="edge_values"):
        FeatureRequirement("lemma", "node", edge_values=False)


def test_contract_rejects_duplicate_feature_requirements() -> None:
    requirement = FeatureRequirement("lemma", "node")

    with pytest.raises(ValueError, match="duplicate"):
        TFArtifactContract(features=(requirement, requirement))


def test_contract_requires_section_types_and_features_together() -> None:
    with pytest.raises(ValueError, match="section"):
        TFArtifactContract(section_types=("document",))


def test_validation_surfaces_cache_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")

    def fail_cleanup(_fabric: Any) -> None:
        raise OSError("cache cleanup denied")

    monkeypatch.setattr(validation_module, "_clear_tf_cache", fail_cleanup)

    with pytest.raises(TFValidationError, match="cache cleanup"):
        validate_tf_artifact(artifact)


def test_validation_preserves_primary_error_when_cache_cleanup_also_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _build_tiny_tf(tmp_path / "tf")
    _corrupt_int_body(artifact / "rank.tf")

    def fail_cleanup(_fabric: Any) -> None:
        raise OSError("cache cleanup denied")

    monkeypatch.setattr(validation_module, "_clear_tf_cache", fail_cleanup)

    with pytest.raises(TFValidationError, match="load") as caught:
        validate_tf_artifact(
            artifact,
            contract=TFArtifactContract(
                features=(FeatureRequirement("rank", "node", value_type="int"),)
            ),
        )

    notes = getattr(caught.value, "__notes__", ())
    assert any("cache cleanup" in note for note in notes)
