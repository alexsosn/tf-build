from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

import tf_build


def test_package_exposes_declared_distribution_version() -> None:
    with (Path(__file__).resolve().parents[1] / "pyproject.toml").open("rb") as handle:
        declared = tomllib.load(handle)["project"]["version"]

    # Editable checkouts and built wheels must expose the same public version.
    assert tf_build.__version__ == declared
    assert tf_build.__version__ == version("tf-build")
