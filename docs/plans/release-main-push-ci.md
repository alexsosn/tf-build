# Issue #92 plan: constrain release CI evidence to main

1. Keep the current manually approved `release.yml` design. No new library/API, action, or credentials.
2. Add deterministic workflow contract regressions first in `tests/test_release_workflow.py`, assert both a `branch=main` API request and a `head_branch == "main"` result selection, plus existing exact SHA/event/success constraints.
3. Run tests against unchanged workflow to observe RED; preserve commit and CI evidence.
4. Modify the existing `gh api` query and its jq predicate in place, without changing other release steps or claiming the candidate has shipped.
5. Run focused tests, Ruff, mypy, and all tests; require exact-final-head PR CI across Python 3.11–3.14 including distribution.
6. After implementation freezes, perform logically independent skeptical review of the *actual final diff*: look for shell quoting mistakes, API selector mismatch, run event/status bypass, missing branch identity, stale tests and accidental release behavior change. Post review and merge only on pass.
