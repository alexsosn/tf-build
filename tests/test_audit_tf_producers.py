"""Offline contract tests for the read-only public TF producer audit."""

import base64

import pytest

from scripts.audit_tf_producers import AuditError, audit_inventory


def manifest():
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
    unknown=False,
    issue_state="open",
    ci="on:\n  pull_request:\njobs:\n  test:\n    run: pytest -q\n",
    source=True,
):
    names = ["Corpus-TF", "PG-TF", "utility"]
    if unknown:
        names.append("Unclassified-TF")

    def fetch(url):
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


def test_supported_and_tracked_statuses_are_accepted():
    result = audit_inventory(manifest(), api())
    assert result == {"public_nonfork": 3, "supported": 1, "tracked": 1, "excluded": 1}


def test_unclassified_new_public_repository_fails_closed():
    with pytest.raises(AuditError, match="Unclassified-TF"):
        audit_inventory(manifest(), api(unknown=True))


def test_closed_tracking_issue_fails():
    with pytest.raises(AuditError, match="issue.*3.*open"):
        audit_inventory(manifest(), api(issue_state="closed"))


def test_missing_pr_ci_trigger_fails():
    with pytest.raises(AuditError, match="pull_request"):
        audit_inventory(
            manifest(),
            api(ci="on:\n  push:\n    branches: [main]\n  # pull_request:\n"),
        )


def test_missing_source_evidence_fails():
    with pytest.raises(AuditError, match="src/writer.py"):
        audit_inventory(manifest(), api(source=False))


def test_missing_executable_ci_marker_fails():
    with pytest.raises(AuditError, match="pytest -q"):
        audit_inventory(
            manifest(),
            api(ci="on:\n  pull_request:\njobs:\n  test:\n    run: echo ok\n"),
        )


def test_duplicate_classification_is_rejected():
    m = manifest()
    m["excluded"].append("Corpus-TF")
    with pytest.raises(AuditError, match="both"):
        audit_inventory(m, api())


def test_public_inventory_fetch_failure_is_not_a_pass():
    def fail(_url):
        raise AuditError("rate limited")

    with pytest.raises(AuditError, match="rate limited"):
        audit_inventory(manifest(), fail)


def test_wrong_owner_is_rejected():
    m = manifest()
    m["owner"] = "another-account"
    with pytest.raises(AuditError, match="owner"):
        audit_inventory(m, api())
