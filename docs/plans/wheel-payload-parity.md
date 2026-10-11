# Plan: gate candidate distribution on direct/sdist payload equivalence

Issue #64.

1. Commit RED-first tests before production: make two valid ZIP wheel fixtures with identical `tf_build/` data but different dist-info bytes and ZIP timestamps, then reject a changed module, missing module, added module, duplicate archive member, path traversal, symlink payload and non-package installable file. Exercise command-line selection of exactly one wheel per directory.
2. Implement `scripts/compare_wheel_payloads.py` as a standalone stdlib-only ZIP reader, computing SHA256 over uncompressed bytes. Do not extract or execute entries.
3. Add the comparison immediately after `pip wheel` rebuild from sdist in `.github/workflows/ci.yml` and `.github/workflows/release.yml`, and regression tests confirming both sites invoke it before smoke/publish.
4. Document the parity guarantee and its limits in README. Run exact-head Ruff, strict mypy, pytest on Python 3.11–3.14 and the distribution job with actual direct and sdist-produced wheels.
5. Separate logically independent adversarial review of final files, test fixture limitations, workflow placement and real distribution job logs. No tag/release publication in this ticket.
