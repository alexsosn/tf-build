from __future__ import annotations

import json
import sys

import pytest

from tf_build.report import (
    ArtifactSummary,
    BuildReport,
    GitSourceProvenance,
    Metric,
    PhaseTiming,
    Producer,
    ResourceUsage,
    peak_rss_bytes,
)


def test_git_source_provenance_canonicalizes_sha1_and_sha256() -> None:
    sha1 = GitSourceProvenance("example/upstream", "ABCDEF01" * 5)
    sha256 = GitSourceProvenance("example/upstream", "ABCDEF01" * 8)

    assert sha1.revision == ("abcdef01" * 5)
    assert sha1.object_format == "sha1"
    assert sha256.revision == ("abcdef01" * 8)
    assert sha256.object_format == "sha256"



@pytest.mark.parametrize(
    "repository",
    [
        "/tmp/source",
        "C:/work/source",
        r"C:\\work\\source",
        r"\\\\server\\share\\source",
        "file:///tmp/source",
        "~/source",
    ],
)
def test_git_source_provenance_rejects_local_absolute_or_home_paths(
    repository: str,
) -> None:
    with pytest.raises(ValueError, match="repository"):
        GitSourceProvenance(repository, "a" * 40)

def test_git_source_provenance_rejects_symbolic_revision() -> None:
    with pytest.raises(ValueError, match="40- or 64-hex"):
        GitSourceProvenance("example/upstream", "main")


@pytest.mark.parametrize(
    "path",
    [
        "",
        ".",
        "..",
        "/tmp/tf",
        "C:/tmp/tf",
        "../tf",
        "tf/../other",
        "tf/./feature",
        "tf\\feature",
        "tf//feature",
        "tf/",
    ],
)
def test_artifact_summary_rejects_nonportable_logical_paths(path: str) -> None:
    with pytest.raises(ValueError, match="artifact path"):
        ArtifactSummary(path, files=1, bytes=1)


@pytest.mark.parametrize(
    ("files", "bytes_"),
    [
        (-1, 1),
        (1, -1),
        (True, 1),
        (1, False),
    ],
)
def test_artifact_summary_rejects_invalid_counts(files: int, bytes_: int) -> None:
    with pytest.raises(ValueError):
        ArtifactSummary("tf", files=files, bytes=bytes_)


@pytest.mark.parametrize("seconds", [-1.0, float("nan"), float("inf"), float("-inf")])
def test_phase_timing_requires_finite_nonnegative_seconds(seconds: float) -> None:
    with pytest.raises(ValueError, match="seconds"):
        PhaseTiming("parse", seconds)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), float("-inf")])
def test_metric_rejects_bool_and_nonfinite_numbers(value: int | float) -> None:
    with pytest.raises(ValueError, match="metric"):
        Metric("slots", value)


@pytest.mark.parametrize(
    ("field", "report"),
    [
        (
            "phase",
            BuildReport(
                producer=Producer("converter", "1.0"),
                phases=(PhaseTiming("parse", 1.0), PhaseTiming("parse", 2.0)),
            ),
        ),
        (
            "artifact",
            BuildReport(
                producer=Producer("converter", "1.0"),
                artifacts=(
                    ArtifactSummary("tf", 1, 1),
                    ArtifactSummary("tf", 2, 2),
                ),
            ),
        ),
        (
            "metric",
            BuildReport(
                producer=Producer("converter", "1.0"),
                metrics=(Metric("slots", 1), Metric("slots", 2)),
            ),
        ),
    ],
)
def test_build_report_rejects_duplicate_names(field: str, report: BuildReport) -> None:
    # Construction is intentionally repeated through validate() so parametrized
    # fixtures can express all duplicate classes without hiding which one failed.
    with pytest.raises(ValueError, match=field):
        report.validate()


def test_report_json_is_deterministic_and_portable() -> None:
    report = BuildReport(
        producer=Producer("copticscriptorium-tf", "0.1.0"),
        source=GitSourceProvenance(
            "CopticScriptorium/corpora",
            "3ac067f1709a0012daf39ea8da2fac79980176a5",
        ),
        phases=(
            PhaseTiming("parse", 1.25),
            PhaseTiming("graph", 2.5),
            PhaseTiming("write", 3.75),
        ),
        artifacts=(ArtifactSummary("tf", files=130, bytes=618_769_322),),
        metrics=(
            Metric("source_records", 2628),
            Metric("slots", 2_394_354),
            Metric("nodes", 3_854_785),
            Metric("edges", 2_505_872),
        ),
        resources=ResourceUsage(peak_rss_bytes=7_503_000_000),
    )

    first = report.to_json()
    second = report.to_json()

    assert first == second
    assert first.endswith("\n")
    assert "/tmp/" not in first
    assert "\\\\" not in first

    payload = json.loads(first)
    assert payload["schema"] == 1
    assert payload["producer"] == {"name": "copticscriptorium-tf", "version": "0.1.0"}
    assert payload["source"]["kind"] == "git"
    assert payload["source"]["objectFormat"] == "sha1"
    assert payload["artifacts"] == [{"path": "tf", "files": 130, "bytes": 618_769_322}]
    assert payload["resources"] == {"peakRssBytes": 7_503_000_000}


def test_peak_rss_bytes_has_explicit_platform_semantics() -> None:
    measured = peak_rss_bytes()

    if sys.platform == "darwin" or sys.platform.startswith("linux"):
        assert isinstance(measured, int)
        assert measured > 0
    else:
        assert measured is None
