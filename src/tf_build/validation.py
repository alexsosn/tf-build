"""Clean-reload validation for generated Text-Fabric corpus artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from tf.fabric import Fabric  # type: ignore[import-untyped]

FeatureKind = Literal["node", "edge"]
FeatureValueType = Literal["str", "int"]
ValidationMode = Literal["selective", "exhaustive"]


class TFValidationError(RuntimeError):
    """Raised when a generated Text-Fabric artifact violates its contract."""


def _require_name(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or any(char.isspace() for char in value)
    ):
        raise ValueError(f"{label} must be one non-empty whitespace-free name")


def _require_feature_name(value: str) -> None:
    _require_name(value, "feature name")
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"feature name must not be a path: {value!r}")


@dataclass(frozen=True, slots=True)
class FeatureRequirement:
    """Structural expectation for one node or edge feature."""

    name: str
    kind: FeatureKind
    value_type: FeatureValueType | None = None
    edge_values: bool | None = None

    def __post_init__(self) -> None:
        _require_feature_name(self.name)
        if self.kind not in {"node", "edge"}:
            raise ValueError("feature kind must be 'node' or 'edge'")
        if self.value_type not in {None, "str", "int"}:
            raise ValueError("feature value_type must be 'str', 'int', or None")
        if self.edge_values is not None and not isinstance(self.edge_values, bool):
            raise ValueError("feature edge_values must be bool or None")
        if self.kind != "edge" and self.edge_values is not None:
            raise ValueError("edge_values is valid only for edge feature requirements")


@dataclass(frozen=True, slots=True)
class TFArtifactContract:
    """Corpus-independent structural expectations for a TF artifact."""

    features: tuple[FeatureRequirement, ...] = ()
    text_formats: tuple[str, ...] = ()
    section_types: tuple[str, ...] | None = None
    section_features: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        features = tuple(self.features)
        formats = tuple(self.text_formats)
        section_types = (
            None if self.section_types is None else tuple(self.section_types)
        )
        section_features = (
            None if self.section_features is None else tuple(self.section_features)
        )

        if any(not isinstance(item, FeatureRequirement) for item in features):
            raise ValueError("features must contain FeatureRequirement values")
        names = tuple(item.name for item in features)
        if len(names) != len(set(names)):
            raise ValueError("duplicate feature requirements are not allowed")

        for name in formats:
            _require_name(name, "text format name")
        if len(formats) != len(set(formats)):
            raise ValueError("duplicate text format requirements are not allowed")

        if (section_types is None) != (section_features is None):
            raise ValueError("section types and section features must be supplied together")
        if section_types is not None and section_features is not None:
            if not 1 <= len(section_types) <= 3:
                raise ValueError("section contract must contain one to three levels")
            if len(section_types) != len(section_features):
                raise ValueError("section types and section features must have equal length")
            for name in section_types:
                _require_name(name, "section type")
            for name in section_features:
                _require_feature_name(name)

        object.__setattr__(self, "features", features)
        object.__setattr__(self, "text_formats", formats)
        object.__setattr__(self, "section_types", section_types)
        object.__setattr__(self, "section_features", section_features)


_EMPTY_CONTRACT = TFArtifactContract()


@dataclass(frozen=True, slots=True)
class TFValidationResult:
    """Summary of the structural TF checks that completed successfully."""

    mode: ValidationMode
    node_features: tuple[str, ...]
    edge_features: tuple[str, ...]
    text_formats: tuple[str, ...]
    section_types: tuple[str, ...]
    section_features: tuple[str, ...]


def _regular_feature_file(root: Path, name: str) -> Path:
    path = root / f"{name}.tf"
    if path.is_symlink():
        raise TFValidationError(f"TF feature file is a symlink: {path.name}")
    if not path.is_file():
        raise TFValidationError(f"required TF feature file is missing: {path.name}")
    return path


def _preflight_artifact(path: str | Path, contract: TFArtifactContract) -> Path:
    requested = Path(path)
    if requested.is_symlink():
        raise TFValidationError(f"TF artifact root must not be a symlink: {requested}")
    if not requested.is_dir():
        raise TFValidationError(f"TF artifact root is not a directory: {requested}")
    root = requested.resolve(strict=True)

    for feature_path in root.glob("*.tf"):
        if feature_path.is_symlink():
            raise TFValidationError(
                f"TF artifact contains symlink feature file: {feature_path.name}"
            )
        if not feature_path.is_file():
            raise TFValidationError(
                f"TF artifact contains non-regular feature path: {feature_path.name}"
            )

    for name in ("otype", "oslots"):
        _regular_feature_file(root, name)
    for requirement in contract.features:
        _regular_feature_file(root, requirement.name)
    if contract.text_formats or contract.section_types is not None:
        _regular_feature_file(root, "otext")

    return root


def _explore_features(
    fabric: Any,
    contract: TFArtifactContract,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        catalog = fabric.explore(silent="deep", show=True)
    except Exception as exc:
        raise TFValidationError("Text-Fabric metadata exploration failed") from exc
    if not isinstance(catalog, dict):
        raise TFValidationError("Text-Fabric metadata exploration returned no catalog")

    bad_metadata = tuple(
        sorted(
            name
            for name, feature in fabric.features.items()
            if bool(getattr(feature, "dataError", False))
        )
    )
    if bad_metadata:
        raise TFValidationError(
            "Text-Fabric metadata load failed for: " + ", ".join(bad_metadata)
        )

    nodes = tuple(sorted(str(name) for name in catalog.get("nodes", ())))
    edges = tuple(sorted(str(name) for name in catalog.get("edges", ())))
    node_set = set(nodes)
    edge_set = set(edges)

    for requirement in contract.features:
        name = requirement.name
        if name not in node_set and name not in edge_set:
            raise TFValidationError(f"required TF feature is not discoverable: {name}")
        actual_kind = "node" if name in node_set else "edge"
        if actual_kind != requirement.kind:
            raise TFValidationError(
                f"TF feature {name} is {actual_kind}, expected {requirement.kind}"
            )

        feature = fabric.features[name]
        actual_type = str(getattr(feature, "dataType", ""))
        if requirement.value_type is not None and actual_type != requirement.value_type:
            raise TFValidationError(
                f"TF feature {name} has value type {actual_type!r}, "
                f"expected {requirement.value_type!r}"
            )

        if requirement.edge_values is not None:
            actual_edge_values = bool(getattr(feature, "edgeValues", False))
            if actual_edge_values != requirement.edge_values:
                raise TFValidationError(
                    f"TF feature {name} edgeValues={actual_edge_values}, "
                    f"expected {requirement.edge_values}"
                )

    return nodes, edges


def _resolve_api(fabric: Any, loaded: Any, mode: ValidationMode) -> Any:
    if loaded is False or loaded is None:
        raise TFValidationError(f"{mode} Text-Fabric load failed")
    if loaded is True:
        api = getattr(fabric, "api", None)
        if api is None:
            raise TFValidationError(
                f"{mode} Text-Fabric load returned success without an API"
            )
        return api
    return loaded


def _runtime_validate(
    fabric: Any,
    *,
    contract: TFArtifactContract,
    mode: ValidationMode,
    node_features: tuple[str, ...],
    edge_features: tuple[str, ...],
) -> TFValidationResult:
    if mode == "selective":
        requested = tuple(requirement.name for requirement in contract.features)
        try:
            loaded = fabric.load(requested, silent="deep")
        except Exception as exc:
            raise TFValidationError("selective Text-Fabric load failed") from exc
        api = _resolve_api(fabric, loaded, mode)
    else:
        try:
            initial = fabric.load("", silent="deep")
        except Exception as exc:
            raise TFValidationError("exhaustive Text-Fabric initial load failed") from exc
        api = _resolve_api(fabric, initial, mode)
        loadable = tuple(
            name
            for name in (*node_features, *edge_features)
            if name not in {"otype", "oslots"}
        )
        if loadable:
            try:
                added = fabric.load(loadable, add=True, silent="deep")
            except Exception as exc:
                raise TFValidationError("exhaustive Text-Fabric add-load failed") from exc
            if added is not True:
                raise TFValidationError("exhaustive Text-Fabric add-load failed")
            api = getattr(fabric, "api", api)

    required_names = tuple(requirement.name for requirement in contract.features)
    if required_names:
        runtime_info = api.isLoaded(required_names, pretty=False)
        if not isinstance(runtime_info, dict):
            raise TFValidationError("Text-Fabric did not report runtime feature status")
        missing_runtime = tuple(
            name for name in required_names if runtime_info.get(name) is None
        )
        if missing_runtime:
            raise TFValidationError(
                "required TF features did not load: " + ", ".join(missing_runtime)
            )

    if mode == "exhaustive":
        discovered = tuple(sorted(set((*node_features, *edge_features))))
        runtime_info = api.isLoaded(discovered, pretty=False)
        if not isinstance(runtime_info, dict):
            raise TFValidationError("Text-Fabric did not report exhaustive feature status")
        missing_runtime = tuple(
            name for name in discovered if runtime_info.get(name) is None
        )
        if missing_runtime:
            raise TFValidationError(
                "exhaustive Text-Fabric load omitted: " + ", ".join(missing_runtime)
            )

    text_api = api.T
    formats = tuple(sorted(str(name) for name in getattr(text_api, "formats", {})))
    for name in contract.text_formats:
        if name not in formats:
            raise TFValidationError(f"required TF text format is missing: {name}")

    section_types = tuple(str(name) for name in getattr(text_api, "sectionTypes", ()))
    section_features = tuple(
        str(name) for name in getattr(text_api, "sectionFeatures", ())
    )
    if contract.section_types is not None:
        if section_types != contract.section_types:
            raise TFValidationError(
                f"TF section types {section_types!r} do not match "
                f"{contract.section_types!r}"
            )
        if section_features != contract.section_features:
            raise TFValidationError(
                f"TF section features {section_features!r} do not match "
                f"{contract.section_features!r}"
            )

    return TFValidationResult(
        mode=mode,
        node_features=node_features,
        edge_features=edge_features,
        text_formats=formats,
        section_types=section_types,
        section_features=section_features,
    )


def _clear_tf_cache(fabric: Any) -> None:
    fabric.clearCache()


def validate_tf_artifact(
    path: str | Path,
    *,
    contract: TFArtifactContract = _EMPTY_CONTRACT,
    mode: ValidationMode = "selective",
) -> TFValidationResult:
    """Validate one generated TF corpus artifact through a fresh TF runtime load."""

    if not isinstance(contract, TFArtifactContract):
        raise ValueError("contract must be a TFArtifactContract")
    if mode not in {"selective", "exhaustive"}:
        raise ValueError("mode must be 'selective' or 'exhaustive'")

    root = _preflight_artifact(path, contract)
    try:
        fabric = Fabric(locations=str(root), silent="deep")
    except Exception as exc:
        raise TFValidationError("could not initialize Text-Fabric for artifact") from exc

    node_features, edge_features = _explore_features(fabric, contract)

    try:
        result = _runtime_validate(
            fabric,
            contract=contract,
            mode=mode,
            node_features=node_features,
            edge_features=edge_features,
        )
    except TFValidationError as error:
        try:
            _clear_tf_cache(fabric)
        except Exception as cleanup_error:
            error.add_note(
                f"Text-Fabric cache cleanup failed for {root}: {cleanup_error}"
            )
        raise
    except Exception as cause:
        error = TFValidationError(f"{mode} Text-Fabric validation failed")
        try:
            _clear_tf_cache(fabric)
        except Exception as cleanup_error:
            error.add_note(
                f"Text-Fabric cache cleanup failed for {root}: {cleanup_error}"
            )
        raise error from cause

    try:
        _clear_tf_cache(fabric)
    except Exception as cleanup_error:
        raise TFValidationError(
            f"Text-Fabric cache cleanup failed for {root}"
        ) from cleanup_error

    return result


__all__ = [
    "FeatureRequirement",
    "TFArtifactContract",
    "TFValidationError",
    "TFValidationResult",
    "validate_tf_artifact",
]
