# Plan: enforce runtime metadata parity for direct and sdist wheels (#68)

1. Commit tests first using tiny real ZIP wheels with identical Python source but altered `Requires-Dist`, `Requires-Python`, `Provides-Extra`, `Name`, `Version`, or `entry_points.txt`; verify the unchanged implementation accepts invalid pairs (RED). Keep a Summary/RECORD variation that passes.
2. Require exactly one readable `METADATA` under a single `.dist-info` root in each wheel; limit bytes while reading and reject missing/ambiguous runtime fields, duplicate Name/Version or oversized metadata.
3. In the existing ZIP loop, record normalized runtime field multisets (order-insensitive, duplicates preserved) and exact optional entry point bytes. After package hash parity succeeds, compare runtime contracts and fail on differences. Do not execute/extract.
4. Run focused pytest, full pytest, Ruff and strict mypy; require exact-head GitHub Actions matrix 3.11–3.14 and real wheel/sdist distribution. Independently review edge cases, including metadata header folding and manifest/release cross-check.
5. Merge only with reviewed exact head; do not create a tag or release. Parent release issue #60 remains open.
