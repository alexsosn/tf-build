from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest

import tf_build
from scripts.check_installed_wheel import check_distribution


def test_package_exposes_declared_distribution_version() -> None:
    with (Path(__file__).resolve().parents[1] / "pyproject.toml").open("rb") as handle:
        declared = tomllib.load(handle)["project"]["version"]

    # Editable checkouts and built wheels must expose the same public version.
    assert tf_build.__version__ == declared
    assert tf_build.__version__ == version("tf-build")


def test_installed_wheel_checker_rejects_version_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A separate output root makes the editable package appear external, so
    # this reaches the installed-wheel contract before any TF example runs.
    monkeypatch.setattr(tf_build, "__version__", "stale-development-version")
    with pytest.raises(RuntimeError, match="does not match distribution"):
        check_distribution(tmp_path)
