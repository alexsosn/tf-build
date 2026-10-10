# Plan: harden scanner open against raced FIFOs and symlinks

Issue: #28

1. RED-first POSIX-only test: start with an actual valid `*.tf` regular file. Monkeypatch `os.open` before the scan, and at the requested feature path assert `O_NONBLOCK | O_NOFOLLOW` **before** swapping the file to a FIFO, then use the real syscall. Require `FeatureReferenceError` and unchanged external state; assertion ensures no hung test without the production fix.
2. RED-first POSIX-only test: similarly replace the feature with a symlink to an external, valid `*.tf`; require a no-follow open and scanner rejection before reading the target.
3. Open with explicit POSIX `O_RDONLY | O_NONBLOCK | O_NOFOLLOW`; on POSIX fail closed if either required flag is not available. On other platforms retain read-only semantics and explicit descriptor type check without claiming POSIX guarantees. `fstat()` and `stat.S_ISREG` must precede `readline()`.
4. Preserve UTF-8 text interpretation, capped 64-Ki-character line and 256-Ki-character total header scan, first-line kind marker requirement, deterministic rendering and cache-directory skip.
5. CI Ruff, strict mypy and real `Fabric.save` tests across Python 3.11–3.14 on exact PR head, then a logically independent adversarial review. This fix does not grant atomic full-tree safety.
