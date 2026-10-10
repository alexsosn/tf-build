# Plan: fail closed on report artifact control characters

Issue #47

1. Commit RED-first tests to `tests/test_report.py`: parametrized NUL, LF, CR, TAB and DEL in relative artifact names and multiple components. Assert `ArtifactSummary` raises `ValueError` with a stable, value-free error; retain a positive test for valid nested Unicode and POSIX punctuation.
2. Confirm tests fail against old helper (control cases previously construct and serialize).
3. Add one narrow C0/DEL check in `_validate_artifact_path` before any JSON emission.
4. Document the report portability constraint in README. Do not change unrelated Agora/fingerprint contracts.
5. Exact-head CI on Python 3.11–3.14 (Ruff, strict mypy, real package tests) followed by a logically independent adversarial review. Any fix after review invalidates approval.
