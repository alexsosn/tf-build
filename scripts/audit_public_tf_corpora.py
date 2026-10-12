#!/usr/bin/env python3
"""Fail CI if an owned public TF corpus builder lacks implementation or an open ticket.

This is a deliberately small *portfolio* gate, not a replacement for the
conversion and native-Fabric-load CI tests inside each corpus repository.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

OWNER = "alexsosn"
# Status is reviewed against each default-branch README and converter/CI evidence.
# "implemented" means native TF corpus or module output; release is not required.
IMPLEMENTED = frozenset({
    "BHSA-cantillation-trees", "CATSS-TF", "CTC-TF",
    "CopticScriptorium-TF", "IIP-TF", "ORACC-TF", "ORAEC-TF",
    "Pseudepigrapha-TF", "TLHdig-TF",
})
# Issue must remain OPEN until the implementation is completed and moved above.
TRACKED = {"OpenGreek-TF": 6, "PG-TF": 3}


def is_corpus_builder(repo: dict) -> bool:
    """Recognize TF converter repos, excluding forks, private, and unrelated tools."""
    name = repo["name"]
    return (
        not repo.get("fork", False)
        and not repo.get("private", False)
        and (name.lower().endswith("-tf") or name == "BHSA-cantillation-trees")
    )


def audit(repos: list[dict], get_json, owner: str = OWNER) -> list[str]:
    """Return actionable errors; get_json(path) is injectable for offline tests."""
    found = {r["name"] for r in repos if is_corpus_builder(r)}
    catalogued = IMPLEMENTED | TRACKED.keys()
    errors = []
    for name in sorted(found - catalogued):
        errors.append(f"Untracked public corpus builder {owner}/{name}: classify as implemented or link an open TF implementation issue")
    for name in sorted(catalogued - found):
        errors.append(f"Catalogued TF repo {owner}/{name} missing from public non-fork inventory: investigate rename, visibility, or deletion")

    for name in sorted(found & IMPLEMENTED):
        path = f"/repos/{owner}/{quote(name)}/contents/.github/workflows"
        try:
            workflows = get_json(path)
            if not isinstance(workflows, list) or not any(
                isinstance(w, dict) and w.get("type") == "file"
                and str(w.get("name", "")).endswith((".yml", ".yaml"))
                for w in workflows
            ):
                errors.append(f"{owner}/{name}: native TF is marked implemented but no GitHub Actions workflow was found; add a converter/Fabric-load CI test")
        except (HTTPError, URLError, ValueError) as exc:
            errors.append(f"{owner}/{name}: could not verify GitHub Actions workflows ({exc})")

    for name, issue_number in sorted(TRACKED.items()):
        if name not in found:
            continue
        try:
            issue = get_json(f"/repos/{owner}/{quote(name)}/issues/{issue_number}")
            if not isinstance(issue, dict) or issue.get("state") != "open" or "pull_request" in issue:
                errors.append(f"{owner}/{name}#{issue_number}: no longer an open implementation issue; either implement and test native TF or reopen/replace the issue")
        except (HTTPError, URLError, ValueError) as exc:
            errors.append(f"{owner}/{name}#{issue_number}: cannot verify tracking issue ({exc})")
    return errors


def api_get(path: str, token: str | None = None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "public-tf-corpus-audit"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request("https://api.github.com" + path, headers=headers)
    with urlopen(req, timeout=25) as response:
        return json.load(response)


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    # The GitHub API exposes public repositories of the named user, including
    # forks. Pagination avoids silently overlooking the next repository.
    repos = []
    page = 1
    try:
        while True:
            chunk = api_get(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}", token)
            if not isinstance(chunk, list):
                raise ValueError("invalid public repository listing")
            repos.extend(chunk)
            if len(chunk) < 100:
                break
            page += 1
        errors = audit(repos, lambda p: api_get(p, token))
    except (HTTPError, URLError, ValueError) as exc:
        print(f"GitHub corpus inventory unavailable: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print("ERROR: " + error, file=sys.stderr)
        return 1
    print(f"PASS: {len(IMPLEMENTED)} implemented TF corpus/module builders with Actions workflows; "
          f"{len(TRACKED)} pending TF implementations covered by open issues; "
          f"{len(repos)} public repositories inventoried.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
