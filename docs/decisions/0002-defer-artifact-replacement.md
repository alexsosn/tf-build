# ADR 0002 — Defer generic replacement of published TF artifacts

**Status:** Accepted (research-only; keep create-only publication)  
**Issue:** [#14](https://github.com/alexsosn/tf-build/issues/14)  
**Date:** 2026-10-10

## Problem

`BuildWorkspace` uses private sibling staging and atomic *no-clobber* publication for a **new** artifact. Rebuilding an already published mutable version directory is a separate operation: `Fabric.save(overwrite=True)` may update feature files without deleting obsolete generated files. A generic `overwrite=True` API would conceal both ownership decisions and nonportable atomicity.

## Evidence: two incompatible consuming contracts

### TLHdig-TF: deliberate destructive reset

`programs/build.py::reset_current_output` validates **both** named output targets against `main_parent` and `provenance_parent` before removal. It resets only exactly the two current-version, converter-owned main and provenance trees after source and patch preflight. Sibling version directories are preserved. Its `docs/research-clean-current-output.md` accepts that failed rebuilds may leave an incomplete current artifact; the old `BUILD-MANIFEST.json` is removed and the result must be revalidated. Old-artifact availability and rollback are explicitly not promised.

### CopticScriptorium-TF: create-only, no replacement

`copticscriptorium_tf/writer.py::write_graph` refuses an existing destination, stages a complete artifact in a sibling temporary directory and publishes without clobbering after structural checks. It does not need a replacement contract.

### tf-build's existing primitive

`src/tf_build/workspace.py::BuildWorkspace` validates a **nonexistent** destination, stages in the same parent and uses `publish_path_no_clobber` from `src/tf_build/_atomic.py`. Its pre-existing path protections must not be weakened.

## Platform constraints

`os.replace`/`Path.replace` cannot generally replace a **non-empty** directory atomically, so renaming a complete new tree over an old non-empty tree is not portable.

- Linux `renameat2(RENAME_EXCHANGE)` supports exchanging directory entries on supporting filesystems; a swap gives atomic name exchange but **not automatic rollback** or durable crash recovery.
- macOS has `renamex_np(..., RENAME_SWAP)` on supported volumes, a distinct capability and error surface.
- Windows ordinary rename/replace APIs do not provide the same generic nonempty-directory swap semantics.
- A two-step move `old → backup; new → final` necessarily opens a gap at the public destination. It needs cleanup/recovery rules, locking, and sufficient space for at least two full trees. Cross-platform, crash-safe multi-tree transactionality does not follow from ordinary Python file APIs.

References: [Python os.replace](https://docs.python.org/3/library/os.html#os.replace), [Linux renameat2](https://man7.org/linux/man-pages/man2/renameat2.2.html), [Apple volumeSupportsSwapRenaming](https://developer.apple.com/documentation/foundation/urlresourcevalues/volumesupportsswaprenaming), [Windows MoveFileEx](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexa).

## Decision

**Do not add a generic replacement/overwrite option to `BuildWorkspace` and do not extract TLHdig's destructive reset into tf-build yet.** TLHdig is one demonstrated reset consumer, while Coptic is create-only. Both have correct but different ownership/availability policies.

If another consumer needs explicit reset, consider a **separate, clearly destructive, owner-bound reset API**, with exact approved direct-child targets, all-target preflight, symlink/parent guards and tests proving siblings survive. It must not silently fall back from atomic publication and must not claim old-artifact availability after failure.

If a consumer actually needs uninterrupted replacement, investigate a **capability-gated directory swap/exchange API** in a new ticket, with filesystem and OS checks, exclusive writer coordination, recovery/rollback semantics and tests for crashes, nonempty directories, injected symlinks and incomplete staged data. Fail closed where unavailable; no unsafe two-rename “atomic” fallback.

## Consequences

Published artifacts remain protected by create-only semantics. Consumers that deliberately reset generated current-version trees retain local responsibility for naming, ownership, preflight and availability guarantees. No obsolete TF feature file can be silently preserved under a falsely advertised generic atomic-replacement helper.
