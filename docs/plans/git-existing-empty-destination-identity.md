# Issue #100: implementation plan

1. Read current tf-build and ORAEC contracts; record focused research (this document) and plan before code.
2. Commit a real-Git regression to `tests/test_source.py`: initial existing empty target; after staged tree is verified with the real function, rename the old target aside and create a new empty target. Expect `FileExistsError`, both directories preserved, no residue from staging. On current code this **must fail** because `target.rmdir()` removes the new target and publish succeeds.
3. Run real GitHub CI on **tests-only** commit to observe the functional RED. Preserve SHA/run evidence.
4. Implement minimal destination identity capture and check around existing preexisting-empty path; do not change source revisions, git commands, fresh-target no-clobber, or any public signatures. Update README to state accurately bounded protection.
5. Full exact-head GitHub CI: Python 3.11–3.14 Ruff/mypy/pytest, distribution real installed TF user-facing E2E and offline wheelhouse smoke, public producer audit. Check run logs for actual regression and wheel tests.
6. Independent adversarial review on frozen head, re-derived from code and ORAEC source adapter; explicitly challenge residual check-to-rmdir race and Windows portability. Merge if no blocker.
7. Keep protected publication #60 and ORAEC release consumer #53 unresolved; no release or tag.
