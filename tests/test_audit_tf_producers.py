"""Offline contract tests for the read-only public TF producer audit."""

from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Any

import pytest

from scripts.audit_tf_producers import AuditError, audit_inventory


def manifest() -> dict[str, Any]:
    return {
        "owner": "alexsosn",
        "excluded": ["utility"],
        "producers": {
            "Corpus-TF": {
                "status": "supported",
                "source_path": "src/writer.py",
                "ci_workflow": ".github/workflows/ci.yml",
                "ci_marker": "pytest -q",
            },
            "PG-TF": {
                "status": "tracked",
                "issue": 3,
                "ci_workflow": ".github/workflows/ci.yml",
            },
        },
    }


def api(
    *,
    unknown: bool = False,
    issue_state: str = "open",
    ci: str = "on:\n  pull_request:\njobs:\n  test:\n    run: pytest -q\n",
    source: bool = True,
) -> Callable[[str], Any]:
    names = ["Corpus-TF", "PG-TF", "utility"]
    if unknown:
        names.append("Unclassified-TF")

    def fetch(url: str) -> Any:
        if "/users/alexsosn/repos?" in url:
            if "page=1" in url:
                rows = [
                    {
                        "name": n,
                        "fork": False,
                        "private": False,
                        "owner": {"login": "alexsosn"},
                    }
                    for n in names
                ]
                rows.extend(
                    [
                        {
                            "name": "forked",
                            "fork": True,
                            "private": False,
                            "owner": {"login": "alexsosn"},
                        },
                        {
                            "name": "private",
                            "fork": False,
                            "private": True,
                            "owner": {"login": "alexsosn"},
                        },
                    ]
                )
                return rows
            return []
        if url.endswith("/issues/3"):
            return {"number": 3, "state": issue_state, "title": "Add Text-Fabric converter"}
        if "/contents/src/writer.py" in url:
            if not source:
                raise AuditError("HTTP 404")
            content = base64.b64encode(b"from tf.fabric import Fabric\n").decode()
            return {"type": "file", "content": content, "encoding": "base64"}
        if "/contents/.github/workflows/ci.yml" in url:
            content = base64.b64encode(ci.encode()).decode()
            return {"type": "file", "content": content, "encoding": "base64"}
        raise AuditError(f"unexpected API URL: {url}")

    return fetch


def test_supported_and_tracked_statuses_are_accepted() -> None:
    result = audit_inventory(manifest(), api())
    assert result == {"public_nonfork": 3, "supported": 1, "tracked": 1, "excluded": 1}


def test_unclassified_new_public_repository_fails_closed() -> None:
    with pytest.raises(AuditError, match="Unclassified-TF"):
        audit_inventory(manifest(), api(unknown=True))


def test_closed_tracking_issue_fails() -> None:
    with pytest.raises(AuditError, match="issue.*3.*open"):
        audit_inventory(manifest(), api(issue_state="closed"))


def test_missing_pr_ci_trigger_fails() -> None:
    with pytest.raises(AuditError, match="pull_request"):
        audit_inventory(
            manifest(),
            api(ci="on:\n  push:\n    branches: [main]\n  # pull_request:\n"),
        )


def test_missing_source_evidence_fails() -> None:
    with pytest.raises(AuditError, match="src/writer.py"):
        audit_inventory(manifest(), api(source=False))


def test_missing_executable_ci_marker_fails() -> None:
    with pytest.raises(AuditError, match="pytest -q"):
        audit_inventory(
            manifest(),
            api(ci="on:\n  pull_request:\njobs:\n  test:\n    run: echo ok\n"),
        )


def test_duplicate_classification_is_rejected() -> None:
    m = manifest()
    m["excluded"].append("Corpus-TF")
    with pytest.raises(AuditError, match="both"):
        audit_inventory(m, api())


def test_public_inventory_fetch_failure_is_not_a_pass() -> None:
    def fail(_url: str) -> Any:
        raise AuditError("rate limited")

    with pytest.raises(AuditError, match="rate limited"):
        audit_inventory(manifest(), fail)


def test_wrong_owner_is_rejected() -> None:
    m = manifest()
    m["owner"] = "another-account"
    with pytest.raises(AuditError, match="owner"):
        audit_inventory(m, api())


def test_commented_ci_command_is_not_accepted_as_executable() -> None:
    only_commented = (
        "on:\n  pull_request:\njobs:\n  test:\n"
        "    steps:\n      - run: echo hello\n      # pytest -q\n"
    )
    with pytest.raises(AuditError, match="pytest -q"):
        audit_inventory(manifest(), api(ci=only_commented))


def test_full_first_page_paginates_to_second_page() -> None:
    policy = manifest()
    extra = [f"other-{i:03d}" for i in range(98)]
    policy["excluded"].extend(extra)

    def entry(name: str) -> dict[str, Any]:
        return {
            "name": name,
            "owner": {"login": "alexsosn"},
            "fork": False,
            "private": False,
        }

    rows = [entry("Corpus-TF"), entry("PG-TF"), *(entry(n) for n in extra)]
    assert len(rows) == 100
    delegate = api()

    def fetch(url: str) -> Any:
        if "/users/alexsosn/repos?" in url:
            if url.endswith("&page=1"):
                return rows
            if url.endswith("&page=2"):
                return [entry("utility")]
            raise AssertionError(f"unexpected page: {url}")
        return delegate(url)

    assert audit_inventory(policy, fetch) == {
        "public_nonfork": 101,
        "supported": 1,
        "tracked": 1,
        "excluded": 99,
    }
