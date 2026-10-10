# Plan: credential-safe Git subprocess error chains

Issue #32, integrated in PR #31 because it shares the same `_run_git` subprocess boundary.

1. RED-first parametrized tests inject actual `subprocess.TimeoutExpired`, `subprocess.CalledProcessError`, and `OSError` from a mocked `git remote add origin SECRET_URL`; assertions inspect both public `str(GitSourceError)` and `"".join(traceback.format_exception(error))` and require absence of `SECRET`.
2. Preserve per-command timeout enforcement and cause type/timeout/status for meaningful debugging, but construct sanitized cause without untrusted `cmd` arguments. For generic `OSError`, suppress raw traceback context instead of revealing paths/credentials.
3. Verify all failure paths clean private staging, including after the destination preexists empty. Keep exact revision fetch and existing tests intact.
4. Run Ruff, mypy, real Git tests across Python 3.11–3.14 on combined exact head, then genuinely independent adversarial review of both timeout and redaction.
5. Deliberate limit: caller application code can still introspect `__context__` containing the original process exception; we only promise no leaking through conventional exception formatting, not redaction of the caller-provided repository string from Python memory.
