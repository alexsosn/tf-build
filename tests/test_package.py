from __future__ import annotations

import tf_build


def test_package_exposes_version() -> None:
    assert tf_build.__version__ == "0.1.0.dev0"
