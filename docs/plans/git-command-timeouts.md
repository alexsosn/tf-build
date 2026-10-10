# Plan: Git command timeouts with RED-first tests

Issue: #30

1. Add RED tests before implementation:
   - A mocked `subprocess.run` asserts a positive `timeout` is supplied and raises `subprocess.TimeoutExpired` for `git fetch`; public API should raise `GitSourceError`, clean private staging, preserve an empty preexisting destination, and retain exception cause.
   - A mocked `subprocess.run` asserts a caller timeout also reaches verification commands such as `rev-parse`, reports the attempted operation without echoing secret-containing argument values.
   - Reject zero, negative, NaN, infinity, bool and nonnumeric values at both public entrypoints **before creating paths**.
   - Run a genuine local `git init/commit/fetch` fixture with an explicit timeout as a passing integration case.
2. Implement minimal production changes: validate once at public boundary, thread timeout through `_run_git` and nested verification, catch `TimeoutExpired` separately with `GitSourceError`.
3. Update existing monkeypatched `verify_git_source` test double to accept the new keyword; do not weaken its destination-race assertion.
4. Document caller override, 30-minute per-command default and precise limitations.
5. Exact-head Ruff/mypy/pytest Python 3.11–3.14, then separate skeptical review focusing on cleanup, argument disclosure and subprocess semantics. No shell, retry or new network dependency.
