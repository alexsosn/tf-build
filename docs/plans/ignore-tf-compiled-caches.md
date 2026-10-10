# Plan: source-backed TF validation

Issue #33

1. RED-first integration regression: build tiny real TF graph, run `validate_tf_artifact(level="all")` to generate a `count.tfx` compiled cache, then corrupt the raw `@valueType=int` feature and restore its original `mtime_ns`. Assert `level="all"` now rejects the raw body, despite bin cache being newer. Assert `level="selected"` rejects when count is explicitly required; `metadata` may succeed because its contract does not parse bodies.
2. Assert caller's `.tf` bytes/caches are unchanged by validation and that no private verification directory remains after success or failure. Preserve successful and failed original source tests.
3. Implement private temporary source-only directory for `selected`/`all` with regular `*.tf` files only. Prefer hardlink for zero-copy, with a safe file-copy fallback. Check symlinks and nonregular candidates, and never include preexisting compiled `.tf/` caches in the view.
4. Call `Fabric` on that view, preserving the existing metadata/depth/required-feature validation flow. Ensure cleanup via a context manager on exceptions.
5. Document extra temporary link/disk-I/O cost and the lack of an atomic concurrent mutation snapshot, and keep `metadata` lightweight.
6. Ruff, strict mypy and real TF pytest across Python 3.11–3.14, plus a logically independent adversarial review grounded in upstream `Data.load` and actual stale-cache test.
