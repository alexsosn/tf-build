# Issue #100: existing-empty Git checkout destination ownership

## Grounded consumer and source evidence

`tf_build.source.fetch_git_source(repository,destination,revision=...)` supports a pre-existing empty directory. ORAEC-TF current `src/oraec_tf/source.py::fetch_source` delegates to this helper, with 40-hex revision and ORAEC error-contract adapter. The helper checks the destination at entry, performs pinned real Git initialization/fetch/detached checkout, verifies the entire new staging tree, and then executes `target.rmdir()` based only on its earlier `target_preexisted` boolean. An attacker or competing actor could have renamed the first empty destination away and created a second empty directory at the same pathname during the fetch. `rmdir()` then removes the second directory, and the later atomic no-clobber publish succeeds: the new empty directory's ownership is silently discarded. The no-clobber rename alone cannot prevent deletion *before* rename.

ORAEC-TF `src/oraec_tf/agora.py::materialize` implements a more defensive analogous check for an existing empty output root: record `lstat().st_dev/st_ino` before work, recheck before `rmdir()`, and refuse replacement. This is meaningful existing consumer precedent, not a speculative new API.

## Contract and security limits

Store the accepted existing-empty directory identity at initial preflight (POSIX/Windows `st_dev/st_ino`), then require it immediately before removing that directory. A mismatch or disappearance raises `FileExistsError` before any deletion, preserves any new occupant, and removes unpublished Git staging. For fresh targets, use the existing atomic no-clobber rename unmodified. For unchanged empty directories, preserve backward-compatible success. Avoid attempting to restore an original caller directory moved elsewhere.

This check materially narrows the long fetch-to-publish race but **cannot** make the final identity check plus path-based `rmdir()` atomic. Concurrency within those instructions could still replace the target. Do not claim lock-free transactional ownership, and do not introduce nonportable filesystem tricks without a demonstrated consumer need.

## Independent oracle

A real local Git repository (no network), real git checkout and detached SHA verification, plus monkeypatched `verify_git_source` wrapper only for a deterministic atomic move/create of the target *after real verification*. Rejected replacement must remain intact/empty; old moved directory remains; staging gone. The pre-fix code incorrectly returns success, proving RED before implementation.
