"""Structural and runtime validation of emitted Text-Fabric artifacts.

Text-Fabric can generate compiled .tf/ caches during runtime loading; source .tf
feature files are never intentionally rewritten by this validator.
"""

from __future__ import annotations

import errno
import os
import shutil
import stat
import tempfile
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tf.fabric import Fabric  # type: ignore[import-untyped]

ValidationLevel = Literal["metadata", "selected", "all"]
FeatureKind = Literal["node", "edge", "config"]
ValueType = Literal["str", "int"]


class ArtifactValidationError(ValueError):
    """The generated Text-Fabric artifact did not satisfy its requested contract."""


@dataclass(frozen=True, slots=True)
class FeatureRequirement:
    """A corpus-neutral requirement on one emitted Text-Fabric feature."""

    name: str
    kind: FeatureKind | None = None
    value_type: ValueType | None = None
    edge_values: bool | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name
            or self.name in {".", ".."}
            or any(char in self.name for char in ("/", "\\"))
            or any(char.isspace() for char in self.name)
        ):
            raise ValueError("feature name must be a non-empty, safe TF filename stem")
        if self.kind not in (None, "node", "edge", "config"):
            raise ValueError(f"unsupported feature kind: {self.kind!r}")
        if self.value_type not in (None, "str", "int"):
            raise ValueError(f"unsupported feature value type: {self.value_type!r}")
        if self.edge_values is not None and self.kind != "edge":
            raise ValueError("edge_values requires kind='edge'")
        if self.kind == "config" and self.value_type is not None:
            raise ValueError("config features have no value_type")


@dataclass(frozen=True, slots=True)
class ArtifactValidation:
    """Evidence of the actual depth of successful artifact verification."""

    level: ValidationLevel
    feature_names: tuple[str, ...]
    required_features: tuple[str, ...]


def _file_features(directory: Path, *, require_otext: bool) -> tuple[str, ...]:
    if directory.is_symlink():
        raise ArtifactValidationError(f"TF artifact directory is a symlink: {directory}")
    if not directory.is_dir():
        raise ArtifactValidationError(
            f"TF artifact directory is missing or not a directory: {directory}"
        )

    features: list[str] = []
    for path in directory.glob("*.tf"):
        if path.is_symlink():
            raise ArtifactValidationError(f"TF feature file is a symlink: {path}")
        if path.is_dir():
            # Text-Fabric's own compiled cache lives in .tf/; other matching
            # directories are likewise not feature files.
            continue
        if not path.is_file():
            raise ArtifactValidationError(f"TF feature path is not a regular file: {path}")
        features.append(path.stem)

    names = tuple(sorted(features))
    for mandatory in ("otype", "oslots", *(("otext",) if require_otext else ())):
        if mandatory not in names:
            raise ArtifactValidationError(f"required TF feature is missing: {mandatory}.tf")
    return names


def _check_metadata(
    fabric: Fabric,
    names: tuple[str, ...],
    requirements: tuple[FeatureRequirement, ...],
) -> dict[str, tuple[str, ...]]:
    try:
        listing = fabric.explore(silent="deep", show=True)
    except Exception as exc:
        raise ArtifactValidationError("Text-Fabric metadata inspection failed") from exc
    if not isinstance(listing, dict):
        raise ArtifactValidationError("Text-Fabric did not return a feature inventory")

    categories: dict[str, tuple[str, ...]] = {
        kind: tuple(listing.get(kind, ()))
        for kind in ("nodes", "edges", "configs")
    }
    discovered = set().union(*map(set, categories.values()))
    for name in names:
        feature = fabric.features.get(name)
        if name not in discovered or feature is None or feature.dataError:
            raise ArtifactValidationError(f"Text-Fabric could not read metadata of feature {name}")
        # TF's Data._setDataType() logs invalid/missing @valueType and then
        # silently substitutes 'str'; the normalized dataType is not proof
        # that the shipped header declared a valid type.
        if not feature.isConfig and feature.metaData.get("valueType") not in ("str", "int"):
            raise ArtifactValidationError(
                f"feature {name} lacks a valid declared @valueType"
            )
        if not feature.isEdge and feature.edgeValues:
            raise ArtifactValidationError(
                f"feature {name} declares @edgeValues but is not an edge"
            )

    for requirement in requirements:
        name = requirement.name
        if name not in names:
            raise ArtifactValidationError(f"required TF feature is missing: {name}")
        feature = fabric.features.get(name)
        if feature is None or feature.dataError:
            raise ArtifactValidationError(f"Text-Fabric could not inspect feature {name}")

        actual_kind: FeatureKind = (
            "config" if feature.isConfig else "edge" if feature.isEdge else "node"
        )
        if requirement.kind is not None and actual_kind != requirement.kind:
            raise ArtifactValidationError(
                f"feature {name} has kind {actual_kind}, expected {requirement.kind}"
            )
        if (
            requirement.value_type is not None
            and feature.metaData.get("valueType") != requirement.value_type
        ):
            raise ArtifactValidationError(
                f"feature {name} declares value type "
                f"{feature.metaData.get('valueType')!r}, "
                f"expected {requirement.value_type}"
            )
        if (
            requirement.edge_values is not None
            and bool(feature.edgeValues) != requirement.edge_values
        ):
            raise ArtifactValidationError(
                f"feature {name} edgeValues={bool(feature.edgeValues)}, "
                f"expected {requirement.edge_values}"
            )
    return categories


def _copy_source_without_following(source: Path, target: Path) -> None:
    """Copy one regular TF feature without blocking on a raced FIFO."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    if os.name == "posix":
        nonblocking = getattr(os, "O_NONBLOCK", None)
        nofollow = getattr(os, "O_NOFOLLOW", None)
        if nonblocking is None or nofollow is None:
            raise ArtifactValidationError("POSIX safe TF source open flags unavailable")
        flags |= nonblocking | nofollow
    with os.fdopen(os.open(source, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ArtifactValidationError(
                f"TF source view includes a nonregular feature: {source.name}"
            )
        with target.open("xb") as output:
            shutil.copyfileobj(stream, output, 1024 * 1024)


@contextmanager
def _uncached_source_view(
    directory: Path,
    names: tuple[str, ...],
) -> Iterator[Path]:
    """Expose shipped TF sources without preexisting Text-Fabric binary caches.

    Hardlinks avoid duplicating multi-gigabyte source data when supported.
    Fabric.load only reads the .tf files; it writes derived caches in the
    temporary location, never in the caller's artifact.
    """
    prefix = ".tf-build-source-verify-"
    try:
        stage = tempfile.TemporaryDirectory(prefix=prefix, dir=directory.parent)
    except OSError as exc:
        # A readable corpus may be installed under a nonwritable parent.
        # Retry only for permission/read-only filesystem failures, never for
        # unrelated path races or out-of-space errors.
        if exc.errno not in (errno.EACCES, errno.EPERM, errno.EROFS):
            raise ArtifactValidationError(
                "could not create isolated Text-Fabric validation directory"
            ) from exc
        try:
            stage = tempfile.TemporaryDirectory(prefix=prefix)
        except OSError as fallback_error:
            raise ArtifactValidationError(
                "could not create isolated Text-Fabric validation directory"
            ) from fallback_error

    with stage as temp_name:
        temp_path = Path(temp_name)
        for name in names:
            source = directory / f"{name}.tf"
            target = temp_path / source.name
            if source.is_symlink():
                raise ArtifactValidationError(f"TF feature file is a symlink: {source}")
            try:
                try:
                    os.link(source, target, follow_symlinks=False)
                except (OSError, NotImplementedError):
                    _copy_source_without_following(source, target)
                if target.is_symlink() or not target.is_file():
                    raise ArtifactValidationError(
                        f"TF source view includes a nonregular feature: {name}"
                    )
            except OSError as exc:
                raise ArtifactValidationError(
                    f"could not stage TF source feature: {name}"
                ) from exc
        yield temp_path


def _validate_loaded_features(
    path: Path,
    names: tuple[str, ...],
    requirements: tuple[FeatureRequirement, ...],
    level: ValidationLevel,
) -> ArtifactValidation:
    """Execute unchanged Text-Fabric checks against a chosen source view."""
    required_names = tuple(item.name for item in requirements)
    try:
        fabric = Fabric(locations=[str(path)], silent="deep")
    except Exception as exc:
        raise ArtifactValidationError("could not initialize Text-Fabric artifact loader") from exc

    categories = _check_metadata(fabric, names, requirements)
    if level != "metadata":
        to_load = tuple(
            requirement.name
            for requirement in requirements
            if requirement.name in categories["nodes"] + categories["edges"]
            and requirement.name not in {"otype", "oslots"}
        )
        try:
            api = fabric.load(to_load, silent="deep")
        except Exception as exc:
            raise ArtifactValidationError("Text-Fabric selected feature load failed") from exc
        if api is None or isinstance(api, bool):
            raise ArtifactValidationError("Text-Fabric selected feature load failed")

        if level == "all":
            all_names = tuple(
                sorted(
                    (set(categories["nodes"]) | set(categories["edges"]))
                    - {"otype", "oslots"}
                )
            )
            try:
                good = fabric.load(all_names, add=True, silent="deep")
            except Exception as exc:
                raise ArtifactValidationError("Text-Fabric exhaustive feature load failed") from exc
            if good is not True:
                raise ArtifactValidationError("Text-Fabric exhaustive feature load failed")

    return ArtifactValidation(
        level=level,
        feature_names=names,
        required_features=required_names,
    )


def validate_tf_artifact(
    directory: str | Path,
    *,
    required_features: Collection[FeatureRequirement] = (),
    level: ValidationLevel = "selected",
    require_otext: bool = False,
) -> ArtifactValidation:
    """Validate a TF artifact at an explicit inspection/reload depth.

    `metadata` validates headers, not feature bodies. `selected` also loads the
    warp and caller-required features. `all` loads every discovered data feature.
    No level claims to validate corpus-specific scholarly semantics.
    """
    if level not in ("metadata", "selected", "all"):
        raise ArtifactValidationError(f"unsupported validation level: {level!r}")

    requirements = tuple(required_features)
    if any(not isinstance(item, FeatureRequirement) for item in requirements):
        raise ArtifactValidationError("required_features must contain FeatureRequirement objects")
    required_names = tuple(item.name for item in requirements)
    if len(set(required_names)) != len(required_names):
        raise ArtifactValidationError("duplicate required TF feature names")

    path = Path(directory)
    names = _file_features(path, require_otext=require_otext)
    if level == "metadata":
        return _validate_loaded_features(path, names, requirements, level)
    # Do not trust a newer .tf/*.tfx cache: Text-Fabric otherwise validates
    # headers while loading possibly stale binary data instead of raw bodies.
    with _uncached_source_view(path, names) as source_view:
        return _validate_loaded_features(source_view, names, requirements, level)


__all__ = [
    "ArtifactValidation",
    "ArtifactValidationError",
    "FeatureRequirement",
    "ValidationLevel",
    "validate_tf_artifact",
]
