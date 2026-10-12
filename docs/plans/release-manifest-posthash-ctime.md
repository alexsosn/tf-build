# Plan: end-of-hash pathname identity completeness (#88)

1. Commit this research and plan before tests and production code.
2. RED-first: add a real POSIX regular file and deterministic second-`Path.lstat` mutation to `tests/test_wheel_manifest.py`. Verify same inode, size, mtime restored, ctime changed and bytes differ. Require the public `scripts.wheel_manifest._identity` to reject the race. Commit test-only on unmodified production and inspect GitHub Actions failure before continuing when possible.
3. Minimal implementation: final path signature comparison includes `st_mtime_ns` and `st_ctime_ns`, agreeing with previously used opened FD signature, and continues rejecting nonregular files and inode swaps. Do not alter SHA256 or archive parsing.
4. Freeze head; run exact-head full Python 3.11–3.14 Ruff, mypy, pytest and real wheel/sdist parity, noneditable installed and offline wheelhouse distribution CI.
5. Logically independent adversarial review against actual diff, race injection, original failure and all CI logs. Post exact-SHA GitHub review, merge only after full GREEN and PASS. Verify post-merge main CI. No releases or tags.
