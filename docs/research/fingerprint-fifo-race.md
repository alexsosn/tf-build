# Research: FIFO replacement race in fingerprint file open

Issue: #24

## Real code and failure boundary

`src/tf_build/fingerprint.py::_files` enumerates the tree using `os.scandir`, calling `is_file(follow_symlinks=False)` to identify candidate regular files. Later `_file_identity` calls `os.open(path, os.O_RDONLY | O_NOFOLLOW)` and only after that checks `fstat(fd)` for `S_ISREG`. In a directory concurrently modified by an adversary, a regular file can be replaced with a named pipe (FIFO) between these two operations.

On POSIX, opening a FIFO for reading with `O_RDONLY` blocks until a writer opens it. Thus the process can hang **before** the later nonregular-file check. `O_NOFOLLOW` is unrelated: a FIFO is not a symlink.

POSIX `O_NONBLOCK` makes opening the FIFO read endpoint return immediately even if no writer is present. It is ignored for ordinary regular file I/O, so it does not change regular-feature byte hashing. The `fstat()` check must remain before the first `read` to reject an accidental FIFO fd.

Reference: Linux [fifo(7)](https://man7.org/linux/man-pages/man7/fifo.7.html) documents ordinary open blocking and nonblocking read-only open. `open(2)` explains `O_NONBLOCK`. POSIX macOS provides the same flag; this code must not infer equivalent semantics on Windows.

## Decision

On POSIX, require and pass `O_NONBLOCK` alongside existing `O_RDONLY | O_NOFOLLOW` for the initial open. Fail closed if the POSIX capability is not available rather than use potentially blocking fallback. Keep the current fstat and streamed hash unchanged. On Windows do not invent a POSIX FIFO guarantee; preserve the original regular-file checks and avoid changing unrelated Windows behavior.

## Scope limitations

This closes a hang in **one** enumerated-file replacement window, not an atomic snapshot or general hostile-directory defense. Directory entry traversal and intermediate path races remain separately documented limitations. No generic locks, external helpers, timeouts or background subprocesses are necessary for ordinary hashing.
