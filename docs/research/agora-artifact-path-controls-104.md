# Agora generated artifact paths and ASCII control characters (#104)

## Research (2026-11-04; recorded before test or production changes)

- On the current `main`, `src/tf_build/agora.py::_relative_path` validates a POSIX-relative name, traversal components, Windows drives, backslashes, reserved Agora provenance-receipt root, and literal NUL. It does **not** reject LF, CR, TAB, other C0 controls or DEL. `agora_output_path` returns a computed path without creating it; allowing a control character can pass preflight silently.
- `src/tf_build/report.py::_validate_artifact_path`, used by `ArtifactSummary`, already rejects any character with ordinal below 32 or exactly 127. A converter composing the current public Agora output path and build report cannot reliably use the same generated artifact filename. `tests/test_report.py::test_report_artifact_path_rejects_control_characters_without_echoing` documents the existing common path invariant.
- Current `tests/test_agora.py` derives its direct and nested layout expectations from Pseudepigrapha and CopticScriptorium, and covers traversal, Windows names, symlinks, NUL in `agora.py` only by implementation, and the root reserved receipt. There is no control-character regression in the Agora output helper.
- The shared behavior is **path validation at the materializer handoff**, not corpus formatting, sanitization, a new API, or filesystem mutation. Valid whitespace within a name (ordinary spaces) and valid Unicode letters must remain valid. A control-character error must not echo untrusted path contents. No new dependencies.

## Plan and acceptance (before production)

1. Add a test that calls the actual public `agora_output_path` on an empty real host-owned directory with C0/DEL characters in both a direct and nested filename, and asserts `AgoraOutputError`, no path creation, and no embedded control text in the exception. Verify rejection also matches `ArtifactSummary` for the identical relative name; retain existing NUL test.
2. Observe real test-only RED against unchanged `src/tf_build/agora.py`; do not count GitHub queued/canceled tests as executed.
3. Change only the NUL-specific check in `_relative_path` to a character-ordinal check aligned with `ArtifactSummary`. Keep the established generic error message, return shape and reserved-root logic.
4. Run exact-final-head Python 3.11–3.14 lint/type/tests plus distribution build, real installed direct/sdist/offline Text-Fabric publication smoke and producer coverage.
5. Perform logically independent skeptical review of complete diff, actual tests and real consumers; merge only on green.

## Explicit limits

This is lexical path validation. It does not make Agora directory traversal atomic against concurrent replacement, replace the host sandbox, validate Text-Fabric feature contents, or create/own the generated artifact. Neither release publication nor consumer pin migration is included.
