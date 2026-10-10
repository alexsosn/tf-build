# Research: safe header-only file opens under concurrent mutation

Issue: #28

## Evidence

The shipped `scan_tf_feature_headers` first enumerates `*.tf` and checks symlink/file type. It then invokes `_read_header(path)`, which calls `Path.open("r", encoding="utf-8")`. A concurrently modified tree can replace a previously regular feature with an unreferenced FIFO or symlink between these calls. POSIX blocking read-only FIFO open may hang before any header is read; symlink replacement may cause inspection of an unrelated file outside the corpus. The initial `Path.is_symlink` does not close either race.

Issue #24 already established the precise POSIX open/TOCTOU behavior for fingerprinting: use `O_RDONLY | O_NONBLOCK | O_NOFOLLOW` for initial opening and `fstat` the resulting descriptor before reading. For ordinary files O_NONBLOCK has no effect on normal streamed byte reading; Windows has no equivalent promised no-follow guarantee in this library.

## Decision

Use the same documented narrow *POSIX* open flags and descriptor classification locally in the feature-header scanner, retaining its bounded, UTF-8 text-mode file streaming. Reject any nonregular opened descriptor with `FeatureReferenceError`; turn OS errors into that public exception. Preserve all semantic/header formatting behavior and pure in-memory rendering.

No universal `safe_open` API: the two consumers need different read/stream contracts, and the preflight is not a concurrent-process security boundary for the whole tree. Directory ancestors can still change after traversal; no atomic artifact snapshot is claimed.
