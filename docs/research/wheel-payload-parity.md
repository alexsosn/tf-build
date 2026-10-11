# Research: equality of direct and sdist-rebuilt wheel code payloads

Issue #64, release blocker #60.

## Code-grounded finding

At main commit 6411907845cc144b1e4c856b81ff403b49007d4b, both CI distribution and manual `release.yml` build a direct wheel using `pip wheel --no-deps`, then build a separate wheel from the emitted `tf_build-*.tar.gz` sdist. `scripts/check_installed_wheel.py` smoke-imports nine public `tf_build` modules and checks two functions; it does **not** enumerate all package code/files. A missing or altered untested module in the source distribution can pass the installed-wheel smoke.

The existing `scripts/wheel_manifest.py` confirms direct wheel metadata/name/version and exact whole-file SHA256, but does not compare the rebuilt wheel payload. ZIP container bytes (compression, timestamps, `RECORD` and generated metadata) need not be byte-identical to assert equivalent installable package content.

## Decision

Compare every regular file under `tf_build/` in each wheel by relative POSIX path and SHA256 of decompressed bytes. Require `tf_build/__init__.py`, nonempty payload, no duplicate entries, no path traversal/absolute/backslash names, no symlink or other exotic file types. Reject non-package file payload outside the wheel's `.dist-info/` (a new data installation surface should receive explicit review). Allow wheel .dist-info files to differ. Stream ZIP entry content while hashing, avoiding whole-wheel buffering. Neither execute code nor extract potentially untrusted ZIP entries.

Run this check in both CI and manually dispatched release pipeline immediately following sdist rebuild, before wheels can be installed, manifested or published. The release retains the separate installed-wheel smoke.

## Constraints

This verifies *package file equivalence*, not byte-identical wheel archives or cryptographically signed provenance. A matching malicious file in both wheels still matches, so independent CI, tests, code review, immutable Git commit and release controls remain mandatory.
