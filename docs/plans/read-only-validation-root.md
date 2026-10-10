# Plan: source-only validation with read-only parent directory

Issue #43

1. RED first. Using real `Fabric.save` corpus fixture, patch `tf_build.validate.tempfile.TemporaryDirectory` to refuse only `dir=artifact.parent` with `PermissionError(errno.EACCES)`. For both `selected` and `all`, assert scratch fallback to OS temp is attempted and the real Text-Fabric loader succeeds. Verify the original `*.tf` files and any pre-existing `.tf/*.tfx` binary caches stay byte-identical and no temporary stage remains.
2. Simulate `os.link` raising `EXDEV` on one source during fallback; verify real safe-copy path works across filesystems. Existing FIFO/symlink race tests remain unchanged.
3. RED negative cases: both locations refuse writes -> public `ArtifactValidationError`, no leaked staging/no success; non-permission sibling failure like `ENOSPC` must not attempt fallback. Optionally corrupt a raw integer feature while leaving its TF binary cache and assert fallback still rejects it.
4. Implement smallest internal helper returning an isolated `TemporaryDirectory`. Preserve sibling fast path; retry system temp only for `EACCES/EPERM/EROFS`. Convert both failures to `ArtifactValidationError`. Keep `_uncached_source_view` source-link/copy and TF load unchanged.
5. Document the behavior and space-cost tradeoff in README. Run exact-head Ruff, strict mypy and real TF pytest on Python 3.11–3.14. Independent skeptical review of both successful source validation and negative source/cache preservation before merging.
