# Plan: bind archive inspection to hashed FD (#80)

1. Commit research and plan from main `da2fce20...`, no implementation changes yet.
2. RED-first tests on actual archive fixtures (ZIP wheel and tar.gz sdist): inspect old valid embedded metadata, atomically substitute a correctly named but invalid-second-archive in the `_check_package_identity` callback, and assert fail-closed. Run real GitHub tests-only CI and record observed failures, including control stable archives.
3. Extend private `_identity(Path, *, inspector: Callable[[BinaryIO], None] | None = None)`. Within the existing safe opened FD and its before/after stat checks, run `inspector(stream)` with that live seekable stream, rewind and chunk-hash **that stream**. Adapt wheel ZIP and sdist TAR inspection to stream callback, preserve existing exception translation/bounded metadata and tar entry checks.
4. Exact frozen-head Ruff, strict mypy, pytest Python 3.11–3.14, actual direct/rebuilt wheel parity, installed wheel/no-index wheelhouse. Correct any detected failures before final review and merge.
5. Same-context but logically independent adversarial review of frozen patch, explicit replacement cases, real CI and resource cleanup, posted to GitHub with commit id. Merge only when all five jobs are successful and head unchanged. Leave #60 release/tag and #53 ORAEC consumer blocked.
