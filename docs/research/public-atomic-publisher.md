# Research: public no-clobber publication for host-owned output roots

Issue #54; second concrete consumer: alexsosn/ORAEC-TF issue #57 / PR #58.

## Two grounded use cases

The shipped `src/tf_build/workspace.py::BuildWorkspace.publish` calls `_atomic.publish_path_no_clobber(staging, final)`; its full lifecycle owns a private sibling staging directory and requires the final path to be *absent from the outset*.

ORAEC's separate Agora host adapter constructs an output containing `tf/` + operational `conversion-summary.json` in an independently managed `tempfile.mkdtemp` sibling. Its external host contract permits an **existing empty** target directory, which must remain until final publication. The adapter therefore requires atomic no-clobber *at the last step*, not a new workspace manager. The old `Path.replace` silently replaced a concurrently created **empty** target on Linux: observed RED CI at ORAEC-TF run 38094392066, while no-clobber regression tests pass after switching to exact-version-pinned private `tf_build._atomic.publish_path_no_clobber`. A public stable entrypoint would avoid external consumers reaching private implementation.

## Platform and filesystem contract

The existing internal primitive already uses `renameat2(RENAME_NOREPLACE)` on Linux, `renamex_np(RENAME_EXCL)` on macOS, and `os.rename` on Windows. It rejects existing destinations including **empty directories**, files and symlinks without a check-then-replace race; unsupported platforms/syscalls or cross-filesystem publication fail closed as OSError. Caller must arrange same-parent/staged source and validate contents first. Atomic naming does not imply file-byte durability/fsync, security against racing ancestor directory changes, or correctness/validation of emitted corpus data.

## Decision

Add a small public `tf_build.publish.publish_path_no_clobber(source: str | Path, destination: str | Path) -> None` that explicitly documents the low-level contract and delegates to the existing `tf_build._atomic` without changing its syscall behavior. Update `BuildWorkspace.publish` to consume this stable facade so the original consumer and external adapters exercise the same public API. No replacement policy, implicit cleanup, universal runner, corpus-specific schema or additional I/O.

Public facade accepts PathLike strings at input boundary for common caller ergonomics; the private primitive continues receiving canonical `Path` objects. Relative names work with standard OS semantics, subject to the same warnings about mutable parent directories. If source and destination coincide, or source is missing, propagate platform errors instead of synthesizing a rename/replacement policy.

## Test and release evidence

Require actual file and directory renames on the CI Linux filesystem, including an intervening **empty** destination inode and nonempty sentinel, successful nested native-TF layout publication, separate symlink path and ordinary error surfacing. RED-first public API contract test fails when the facade is absent, while prior private behavior tests provide behavioral oracles. Run Ruff, strict mypy, pytest Python 3.11–3.14 on exact head, then independent adversarial review. No claim that ORAEC's pinned older SHA automatically gains this API: migrate its dependency after this new commit is built and independently tested.
