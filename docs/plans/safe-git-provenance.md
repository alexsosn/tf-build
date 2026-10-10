# Plan: reject credential-bearing Git source metadata

Issue #35

1. RED-first parametrized tests for control-character parser bypasses and HTTP(S) user:password, HTTP(S) token-only userinfo, query-bearing Git URLs, fragments and SSH password-in-authority. Include percent-encoded userinfo. Assert `GitSourceProvenance` fails before `BuildReport.to_json` can serialize secrets.
2. Extend existing clean locator tests to retain `ssh://git@host/path`, `git@host:org/repo.git`, `https://host/repo.git` and short `owner/repo`.
3. Implement narrow URL-aware checks inside `_validate_repository_locator` using stdlib `urllib.parse.urlsplit`; reject malformed URL authority parse errors, but do not change Git transport or filesystem checks.
4. Document difference between credential-bearing acquisition URL and clean provenance repository identifier, plus limitations of opaque path contents.
5. Full exact-head Ruff/mypy/pytest Python 3.11–3.14 and separate adversarial review of actual serialized BuildReport JSON and all supported locator styles. No API broadening.
