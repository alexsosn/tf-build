"""Read-only audit of the owner's public non-fork TF corpus producers.

This is a *coverage* gate, not a successful TF conversion or scientific audit.
Per-repository CI remains responsible for executing real native TF tests.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com"
FetchJson = Callable[[str], Any]


class AuditError(RuntimeError):
    """A fail-closed inventory, GitHub API, or CI contract violation."""


def github_fetch(path: str) -> Any:
    if not path.startswith("/") or "//" in path:
        raise AuditError(f"unsafe GitHub API path: {path!r}")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "tf-build-public-producer-audit",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(API_ROOT + path, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        # Never include authenticated request headers or tokens in diagnostics.
        raise AuditError(f"GitHub API request failed at {path}: {type(exc).__name__}") from exc


def _repository_names(owner: str, fetch: FetchJson) -> set[str]:
    names: set[str] = set()
    for page in range(1, 101):
        path = f"/users/{quote(owner)}/repos?per_page=100&type=owner&page={page}"
        items = fetch(path)
        if not isinstance(items, list) or len(items) > 100:
            raise AuditError(f"invalid repository API page {page}")
        for repo in items:
            if not isinstance(repo, dict) or not isinstance(repo.get("name"), str):
                raise AuditError("malformed repository record")
            if not isinstance(repo.get("owner"), dict) or repo["owner"].get("login") != owner:
                raise AuditError(f"unexpected repository owner on page {page}")
            if repo.get("fork") is True or repo.get("private") is True:
                continue
            if repo.get("fork") is not False or repo.get("private") is not False:
                raise AuditError("missing fork/private status for public inventory")
            name = repo["name"]
            if name in names:
                raise AuditError(f"duplicate public repository in paginated response: {name}")
            names.add(name)
        if len(items) < 100:
            return names
    raise AuditError("repository listing exceeded 100 pages")


def _read_repository_file(owner: str, repo: str, path: str, fetch: FetchJson) -> str:
    if not path or path.startswith("/") or ".." in path.split("/"):
        raise AuditError(f"invalid evidence path for {repo}: {path}")
    api_path = f"/repos/{quote(owner)}/{quote(repo)}/contents/{quote(path, safe='/')}"
    try:
        result = fetch(api_path)
    except AuditError as exc:
        raise AuditError(f"{repo}: missing or unreadable evidence {path}: {exc}") from exc
    if not isinstance(result, dict) or result.get("type") != "file":
        raise AuditError(f"{repo}: missing regular evidence file {path}")
    if result.get("encoding") != "base64" or not isinstance(result.get("content"), str):
        raise AuditError(f"{repo}: invalid encoded evidence {path}")
    try:
        raw = base64.b64decode(result["content"], validate=False)
        return raw.decode("utf-8")
    except (binascii.Error, UnicodeError) as exc:
        raise AuditError(f"{repo}: invalid UTF-8 evidence {path}") from exc


def _has_pull_request_trigger(workflow: str) -> bool:
    """Only accept a top-level GitHub Actions 'on' pull_request trigger."""
    in_events = False
    for line in workflow.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        uncommented = line.split(" #", 1)[0]
        if not line[0].isspace():
            in_events = uncommented.strip() == "on:"
            if re.fullmatch(r"on:\s*\[[^]]*\bpull_request\b[^]]*\]", uncommented):
                return True
        elif in_events and re.match(r"^  pull_request\s*:", uncommented):
            return True
    return False


def audit_inventory(manifest: dict[str, Any], fetch: FetchJson) -> dict[str, int]:
    owner = manifest.get("owner")
    if owner != "alexsosn":
        raise AuditError("manifest owner must be alexsosn")
    excluded = manifest.get("excluded")
    producers = manifest.get("producers")
    if (
        not isinstance(excluded, list)
        or any(not isinstance(x, str) or not x for x in excluded)
        or len(set(excluded)) != len(excluded)
        or not isinstance(producers, dict)
    ):
        raise AuditError("malformed classification manifest")
    if any(x in producers for x in excluded):
        raise AuditError("repository classified as both excluded and producer")

    observed = _repository_names(owner, fetch)
    classified = set(excluded) | set(producers)
    if observed != classified:
        missing = sorted(observed - classified)
        stale = sorted(classified - observed)
        raise AuditError(f"public non-fork inventory drift: unclassified={missing}; stale={stale}")

    counts = {
        "public_nonfork": len(observed),
        "supported": 0,
        "tracked": 0,
        "excluded": len(excluded),
    }
    for repo, entry in sorted(producers.items()):
        if not isinstance(entry, dict):
            raise AuditError(f"{repo}: malformed policy")
        status = entry.get("status")
        if status not in {"supported", "tracked"}:
            raise AuditError(f"{repo}: invalid status {status!r}")
        workflow_path = entry.get("ci_workflow")
        if not isinstance(workflow_path, str) or not workflow_path.startswith(".github/workflows/"):
            raise AuditError(f"{repo}: missing CI workflow proof")
        workflow = _read_repository_file(owner, repo, workflow_path, fetch)
        if not _has_pull_request_trigger(workflow):
            raise AuditError(f"{repo}: {workflow_path} has no pull_request CI trigger")
        if status == "supported":
            source_path = entry.get("source_path")
            marker = entry.get("ci_marker")
            if (
                not isinstance(source_path, str)
                or not source_path
                or not isinstance(marker, str)
                or not marker
            ):
                raise AuditError(
                    f"{repo}: supported producer lacks source or executable CI evidence"
                )
            _read_repository_file(owner, repo, source_path, fetch)
            executable_lines = (
                line.split(" #", 1)[0]
                for line in workflow.splitlines()
                if not line.lstrip().startswith("#")
            )
            if not any(marker in line for line in executable_lines):
                raise AuditError(f"{repo}: CI workflow lacks required marker {marker!r}")
        else:
            issue = entry.get("issue")
            if not isinstance(issue, int) or isinstance(issue, bool) or issue <= 0:
                raise AuditError(f"{repo}: incomplete producer needs a positive issue number")
            issue_path = f"/repos/{quote(owner)}/{quote(repo)}/issues/{issue}"
            record = fetch(issue_path)
            if (
                not isinstance(record, dict)
                or record.get("state") != "open"
                or "pull_request" in record
            ):
                raise AuditError(
                    f"{repo}: tracking issue #{issue} must remain open until TF support is verified"
                )
        counts[status] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = audit_inventory(manifest, github_fetch)
    except (AuditError, OSError, json.JSONDecodeError) as exc:
        print(f"TF producer inventory FAILED: {exc}", file=sys.stderr)
        return 1
    print("TF producer inventory PASS: " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
