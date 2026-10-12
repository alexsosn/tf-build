"""Release workflows must not publish packages merely on branch pushes."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


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


def test_release_ci_gate_requires_exact_main_push_at_both_filter_boundaries() -> None:
    workflow = (Path(__file__).parents[1] / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )
    assert "head_sha=$TF_RELEASE_SOURCE&event=push&branch=main&per_page=100" in workflow
    assert 'select(.head_sha == "' in workflow
    assert 'select(.event == "push")' in workflow
    assert 'select(.head_branch == "main")' in workflow
    assert 'select(.conclusion == "success")' in workflow


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is not available on this host")
@pytest.mark.parametrize(
    ("runs", "expected"),
    [
        ([{"branch": "feature", "event": "push", "sha": "correct", "status": "success"}], "0"),
        (
            [
                {"branch": "feature", "event": "push", "sha": "correct", "status": "success"},
                {"branch": "main", "event": "push", "sha": "correct", "status": "failure"},
            ],
            "0",
        ),
        ([{"branch": "main", "event": "push", "sha": "correct", "status": "success"}], "1"),
        ([{"branch": "main", "event": "push", "sha": "wrong", "status": "success"}], "0"),
        ([{"branch": "main", "event": "pull_request", "sha": "correct", "status": "success"}], "0"),
    ],
)
def test_release_ci_jq_filter_on_realistic_action_runs(
    runs: list[dict[str, str]], expected: str
) -> None:
    workflow = (Path(__file__).parents[1] / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )
    # Reassemble the actual shell-quoted --jq expression (including source SHA substitution).
    match = re.search(r"--jq '([^']*)'\$TF_RELEASE_SOURCE'([^']*)'", workflow)
    assert match is not None, "cannot find the release workflow's actual gh --jq expression"
    source_sha = "a" * 40
    expression = match.group(1) + source_sha + match.group(2)
    records = {
        "workflow_runs": [
            {
                "head_branch": run["branch"],
                "event": run["event"],
                "head_sha": source_sha if run["sha"] == "correct" else "b" * 40,
                "conclusion": run["status"],
            }
            for run in runs
        ]
    }
    completed = subprocess.run(
        ["jq", "-r", expression],
        input=json.dumps(records),
        text=True,
        capture_output=True,
        check=True,
    )
    assert completed.stdout.strip() == expected
