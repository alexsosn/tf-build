"""The optional PyPI promotion must reuse verified release bytes."""

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_pypi_promotion_has_no_automatic_or_privileged_build_path() -> None:
    workflow = (ROOT / ".github/workflows/publish-pypi.yml").read_text(
        encoding="utf-8"
    )
    assert "on:\n  workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "\n  pull_request:" not in workflow
    prepare, remainder = workflow.split("\n  publish:\n", 1)
    publish, verify = remainder.split("\n  verify-index:\n", 1)
    assert "github.ref == 'refs/heads/main'" in prepare
    assert "git merge-base --is-ancestor" in prepare
    assert "releases/download/" in prepare and "curl --fail" in prepare
    assert "scripts/wheel_manifest.py" in prepare and "--verify-existing" in prepare
    assert "check_installed_wheel.py" in prepare
    assert "tf_build.__version__" in prepare
    assert "actions/upload-artifact@v4" in prepare
    assert "id-token: write" not in prepare + verify
    assert workflow.count("id-token: write") == 1
    assert "environment: pypi" in publish
    assert "needs: prepare" in publish
    assert "actions/download-artifact@v4" in publish
    assert "pypa/gh-action-pypi-publish@release/v1" in publish
    assert "actions/checkout" not in publish
    assert "pip install" not in publish
    assert "contents: write" not in workflow
    assert "needs: [prepare, publish]" in verify
    assert "https://pypi.org/simple" in verify
    assert "download --no-deps" in verify
    assert "cmp " in verify
    assert "check_installed_wheel.py" in verify
    assert "python -m build" not in workflow
    assert "gh release create" not in workflow
