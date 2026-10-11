# Plan: compare required WHEEL installation metadata (#70)

1. Update synthetic wheel fixture to emit genuine WHEEL headers matching purelib py3-none-any by default; allow `None` to model missing WHEEL. Commit RED tests before changing validator: missing/blank/duplicate required headers; invalid Boolean/version/tag; parity mismatch in `Wheel-Version`, `Root-Is-Purelib`, `Tag`, `Build`; successful `Generator` and tag-order differences.
2. Run tests-only PR CI, record failures at baseline. Ruff/mypy should remain green in RED stage.
3. Extend bounded `_runtime_contract` with a private WHEEL parser; compare install-relevant normalized tuples in addition to existing dependency/entrypoint contract. Treat malformed wheel as `WheelPayloadMismatch`, not success or uncaught parsing errors. Avoid extracting/importing wheel payloads.
4. Run complete exact-head Python 3.11–3.14 CI and distribution build (real wheel + emitted sdist roundtrip and offline wheelhouse install), then independent adversarial review based on final diff, official spec, and CI logs.
5. Merge only after all gates. Leave upstream publication #60 and ORAEC consumer #53 open; tag/release creation is out of scope.
