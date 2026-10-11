"""Release workflows must not publish packages merely on branch pushes."""

from pathlib import Path


def test_release_workflow_requires_explicit_manual_dispatch_and_review_boundary() -> None:
    source = (Path(__file__).parents[1] / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )
    assert "on:\n  workflow_dispatch:" in source
    assert "\n  push:" not in source
    assert "\n  pull_request:" not in source
    assert "environment: release" in source
    assert "contents: write" in source
    assert "actions: read" in source
    assert "actions/workflows/ci.yml/runs?head_sha=$TF_RELEASE_SOURCE" in source
    assert '.conclusion == "success"' in source
    assert "git merge-base --is-ancestor" in source
    assert "gh release create" in source
    assert "--verify-tag" in source
    assert "--prerelease" in source
    assert "scripts/wheel_manifest.py" in source
    assert "--sdist-dir" in source
    assert "check_installed_wheel.py" in source
