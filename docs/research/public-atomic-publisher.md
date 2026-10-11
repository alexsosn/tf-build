# Research: reusable no-clobber publication from a second real consumer

Issue: #54.

## Grounding

In tf-build, `src/tf_build/workspace.py::BuildWorkspace.publish` uses the internal `tf_build._atomic.publish_path_no_clobber`. `BuildWorkspace` requires the final destination **absent** on initialization and while entering its context. Its lifecycle intentionally includes private staging and cleanup.

ORAEC-TF issue #57 and PR #58 demonstrate another caller: `src/oraec_tf/agora.py::materialize` must keep an Agora-owned existing **empty output directory** until the outer converter and checks finish. It currently stages sibling `tf/` and `conversion-summary.json`, then removes the old empty directory immediately before promotion. The original `stage.replace(target)` could overwrite a *newly created empty directory* during the race. The consumer has a RED-first real-path test that catches this while a nonempty sentinel test would not.

Current internal atomic implementation uses Linux `renameat2(RENAME_NOREPLACE)`, Darwin `renamex_np(RENAME_EXCL)`, and Windows `os.rename` on supported systems. The flags prohibit replacing a simultaneously created destination—including empty directories, files and symlinks—without relying on a stale check. Unsupported OS/syscall errors fail closed. This provides a low-level publication operation; it does **not** create staging, validate its content, manage an Agora-owned empty destination, or clean up a failed source.

## Decision and API

Make the *existing* function available as a public import from `tf_build.publication`:

```python
from tf_build.publication import publish_path_no_clobber
publish_path_no_clobber(staging_path, final_path)
```

The module re-exports the already-tested internal function rather than forking syscalls or adding a facade with behavior differences. Keep the existing internal import for BuildWorkspace to avoid changing its lifecycle. Public input contract is `pathlib.Path` source and destination, on same filesystem; exactly one OS-atomic rename if supported. On success source is moved, on failure source remains (subject to external concurrent mutation) and the destination is untouched. `FileExistsError` is the expected collision. No automatic validation, cleanup, replacement or transaction semantics are promised.

## Edge cases / non-goals

Test a newly created **empty** competitor and unchanged inode, nonempty destination, destination symlink (including dangling), existing file, fresh publication, missing source, and incompatible/unsupported platform behavior where deterministic mocking is appropriate. Avoid claiming a universal atomic snapshot of concurrent readers or a cross-filesystem operation. Existing host-owned empty target handling remains the consumer's responsibility.

Do not modify the active ORAEC-TF PR #58 concurrently. After its own integration merges, a separate coordinated consumer switch can use the new public import. Before a tagged package release it remains a pre-0.1 API.

Evidence: ORAEC-TF #57/#58 actual code and test patch; tf-build `_atomic.py`, `workspace.py`, and `tests/test_workspace.py`.
