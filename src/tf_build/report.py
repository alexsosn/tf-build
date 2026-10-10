"""Typed operational reports for Text-Fabric materializer runs."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal
from urllib.parse import urlsplit

from .source import GitSourceError, validate_git_revision

SCHEMA = 1


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _require_nonnegative_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _require_finite_number(value: int | float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a numeric value")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} must be finite")


def _validate_repository_locator(repository: str) -> None:
    _require_text(repository, "Git repository")
    if any(ord(char) < 32 or ord(char) == 127 for char in repository):
        raise ValueError("Git repository provenance must not contain control characters")
    lowered = repository.lower()
    path_parts = repository.replace("\\", "/").split("/")
    if (
        lowered.startswith("file:")
        or repository.startswith("\\\\")
        or repository.startswith("~")
        or PurePosixPath(repository).is_absolute()
        or bool(PureWindowsPath(repository).drive)
        or any(part in {".", ".."} for part in path_parts)
    ):
        raise ValueError(
            "Git repository provenance must not be a local absolute/home path"
        )

    if "?" in repository or "#" in repository:
        raise ValueError(
            "Git repository provenance must not contain query or fragment data"
        )
    if "://" in repository:
        try:
            parsed = urlsplit(repository)
            user = parsed.username
            password = parsed.password
        except ValueError as exc:
            raise ValueError("Git repository provenance URL is malformed") from exc
        if user is not None and (
            password is not None or parsed.scheme not in {"ssh", "git+ssh"}
        ):
            raise ValueError(
                "Git repository provenance must not contain URL credentials"
            )


def _validate_artifact_path(path: str) -> None:
    if not isinstance(path, str):
        raise ValueError("artifact path must be a string")
    parts = path.split("/")
    if (
        not path
        or path.startswith("/")
        or bool(PureWindowsPath(path).drive)
        or "\\" in path
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ValueError(
            "artifact path must be a non-empty relative POSIX path without traversal"
        )


@dataclass(frozen=True, slots=True)
class Producer:
    """Identity of the package or application that produced the report."""

    name: str
    version: str

    def __post_init__(self) -> None:
        _require_text(self.name, "producer name")
        _require_text(self.version, "producer version")


@dataclass(frozen=True, slots=True)
class GitSourceProvenance:
    """Caller-declared immutable Git source provenance."""

    repository: str
    revision: str

    def __post_init__(self) -> None:
        _validate_repository_locator(self.repository)
        try:
            revision = validate_git_revision(self.revision)
        except GitSourceError as exc:
            raise ValueError(str(exc)) from exc
        object.__setattr__(self, "revision", revision)

    @property
    def object_format(self) -> Literal["sha1", "sha256"]:
        return "sha1" if len(self.revision) == 40 else "sha256"


@dataclass(frozen=True, slots=True)
class PhaseTiming:
    """Elapsed time for one named materializer phase."""

    name: str
    seconds: float

    def __post_init__(self) -> None:
        _require_text(self.name, "phase name")
        if isinstance(self.seconds, bool) or not isinstance(self.seconds, (int, float)):
            raise ValueError("phase seconds must be a finite non-negative number")
        seconds = float(self.seconds)
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("phase seconds must be a finite non-negative number")
        object.__setattr__(self, "seconds", seconds)


@dataclass(frozen=True, slots=True)
class ArtifactSummary:
    """Operational size/count summary for one logical artifact."""

    path: str
    files: int
    bytes: int

    def __post_init__(self) -> None:
        _validate_artifact_path(self.path)
        _require_nonnegative_int(self.files, "artifact files")
        _require_nonnegative_int(self.bytes, "artifact bytes")


@dataclass(frozen=True, slots=True)
class Metric:
    """One small numeric operational metric."""

    name: str
    value: int | float
    unit: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.name, "metric name")
        _require_finite_number(self.value, "metric value")
        if self.unit is not None:
            _require_text(self.unit, "metric unit")


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    """Portable subset of measured process resource usage."""

    peak_rss_bytes: int | None = None

    def __post_init__(self) -> None:
        if self.peak_rss_bytes is not None:
            _require_nonnegative_int(self.peak_rss_bytes, "peak RSS bytes")


@dataclass(frozen=True, slots=True)
class BuildReport:
    """Successful operational materializer report.

    The report is not an artifact identity or release-certification manifest.
    """

    producer: Producer
    source: GitSourceProvenance | None = None
    phases: tuple[PhaseTiming, ...] = ()
    artifacts: tuple[ArtifactSummary, ...] = ()
    metrics: tuple[Metric, ...] = ()
    resources: ResourceUsage | None = None

    def validate(self) -> None:
        self._require_unique(
            "phase",
            tuple(phase.name for phase in self.phases),
        )
        self._require_unique(
            "artifact",
            tuple(artifact.path for artifact in self.artifacts),
        )
        self._require_unique(
            "metric",
            tuple(metric.name for metric in self.metrics),
        )

    @staticmethod
    def _require_unique(label: str, values: tuple[str, ...]) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {label} names are not allowed")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "producer": {
                "name": self.producer.name,
                "version": self.producer.version,
            },
            "source": (
                None
                if self.source is None
                else {
                    "kind": "git",
                    "repository": self.source.repository,
                    "revision": self.source.revision,
                    "objectFormat": self.source.object_format,
                }
            ),
            "phases": [
                {"name": phase.name, "seconds": phase.seconds}
                for phase in self.phases
            ],
            "artifacts": [
                {
                    "path": artifact.path,
                    "files": artifact.files,
                    "bytes": artifact.bytes,
                }
                for artifact in self.artifacts
            ],
            "metrics": [
                {
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                }
                for metric in self.metrics
            ],
            "resources": (
                None
                if self.resources is None
                else {"peakRssBytes": self.resources.peak_rss_bytes}
            ),
        }

    def to_json(self) -> str:
        """Serialize deterministically for a fixed report value."""
        return (
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        )


def peak_rss_bytes() -> int | None:
    """Return current-process peak RSS in bytes where stdlib units are known."""
    if sys.platform != "darwin" and not sys.platform.startswith("linux"):
        return None

    try:
        import resource
    except ImportError:  # pragma: no cover - resource is present on supported Unix.
        return None

    raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        return raw
    return raw * 1024


__all__ = [
    "ArtifactSummary",
    "BuildReport",
    "GitSourceProvenance",
    "Metric",
    "PhaseTiming",
    "Producer",
    "ResourceUsage",
    "peak_rss_bytes",
]
