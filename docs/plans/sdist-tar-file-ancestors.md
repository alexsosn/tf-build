# Plan: reject implicit regular-file ancestors in sdist manifests (#74)

1. On branch from main `dca00f32...`, commit research and this plan (no production changes).
2. RED-only regression tests using `tarfile.open(mode="w:gz")`, genuine `TarInfo` regular files/directories: file ancestor `pkg` vs `pkg/mod.py` in both orders; regular root with PKG-INFO; positive explicit directory with implicit ancestor and child. Run GitHub CI against tests-only head to record failures.
3. Implement minimal `files: set[str]` and `directories: set[str]` state inside `_sdist_identity`. Reject any ancestor of an entry that is already a regular file and any regular member name that was previously inferred to be a directory. Keep existing explicit entry deduplication. Add parents to directory state before processing next entry.
4. Run exact-head Ruff, mypy, pytest matrix Python 3.11, 3.12, 3.13, 3.14 and real packaging job with two wheel builds, sdist, installed-wheel and offline prepared wheelhouse.
5. Perform a fresh adversarial review against the actual frozen patch and the real tar test evidence; post as a same-context COMMENT review, never misrepresent as separate reviewer approval. Fix-and-retest any blockers. Merge only after the final reviewed head passes. Owner-controlled release tag and ORAEC consumer migration remain out of scope.
