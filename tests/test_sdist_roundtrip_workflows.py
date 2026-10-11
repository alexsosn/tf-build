"""Contract: publishable sdist must reconstruct a usable noneditable wheel."""

from pathlib import Path

import pytest


@pytest.mark.parametrize("filename", ["ci.yml", "release.yml"])
def test_both_distribution_paths_smoke_a_wheel_rebuilt_from_real_sdist(
    filename: str,
) -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / filename
    ).read_text(encoding="utf-8")
    assert "Rebuild and smoke-install wheel from emitted sdist" in workflow
    assert 'pip wheel --no-deps --wheel-dir "$RUNNER_TEMP/sdist-wheels"' in workflow
    assert '"$RUNNER_TEMP"/sdist/tf_build-*.tar.gz' in workflow
    assert 'pip install "$RUNNER_TEMP"/sdist-wheels/tf_build-*.whl' in workflow
    assert '"$RUNNER_TEMP/sdist-wheel-venv/bin/python"' in workflow
    assert '"$GITHUB_WORKSPACE/scripts/check_installed_wheel.py"' in workflow
