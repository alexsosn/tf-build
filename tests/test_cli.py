"""Researcher CLI tests execute the installed-module boundary on real native TF files."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.tiny_tf_publication import publish_tiny_corpus


@pytest.fixture
def artifact(tmp_path: Path) -> Path:
    destination = tmp_path / "emitted-tf"
    publish_tiny_corpus(destination)
    return destination


def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tf_build", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def test_researcher_cli_exhaustively_reloads_real_tf_without_mutating_sources(
    tmp_path: Path, artifact: Path
) -> None:
    before = {
        path.name: path.read_bytes()
        for path in artifact.glob("*.tf")
    }
    result = _cli(tmp_path, "validate", str(artifact), "--require-otext")
    assert result.returncode == 0, result.stderr
    inspected = json.loads(result.stdout)
    assert inspected == {
        "feature_names": sorted(before),
        "level": "all",
        "required_features": [],
    }
    assert {
        path.name: path.read_bytes()
        for path in artifact.glob("*.tf")
    } == before


def test_researcher_cli_exposes_validation_depth(tmp_path: Path, artifact: Path) -> None:
    for level in ("metadata", "selected", "all"):
        result = _cli(tmp_path, "validate", str(artifact), "--level", level)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["level"] == level


def test_researcher_cli_rejects_missing_warp_without_success_json(
    tmp_path: Path, artifact: Path
) -> None:
    (artifact / "oslots.tf").unlink()
    result = _cli(tmp_path, "validate", str(artifact))
    assert result.returncode != 0
    assert result.stdout == ""
    assert "oslots.tf" in result.stderr
    assert "Traceback" not in result.stderr


def test_researcher_cli_optional_otext_is_an_explicit_contract(
    tmp_path: Path, artifact: Path
) -> None:
    (artifact / "otext.tf").unlink()
    ordinary = _cli(tmp_path, "validate", str(artifact), "--level", "metadata")
    assert ordinary.returncode == 0, ordinary.stderr
    required = _cli(
        tmp_path, "validate", str(artifact), "--level", "metadata", "--require-otext"
    )
    assert required.returncode != 0
    assert required.stdout == ""
    assert "otext.tf" in required.stderr


def test_researcher_cli_help_and_invalid_level(tmp_path: Path) -> None:
    help_result = _cli(tmp_path, "--help")
    assert help_result.returncode == 0
    assert "validate" in help_result.stdout
    invalid = _cli(tmp_path, "validate", "irrelevant", "--level", "invented")
    assert invalid.returncode != 0
    assert invalid.stdout == ""
    assert "invalid choice" in invalid.stderr
