# Research: detect posthash same-inode release archive mutation (#88)

## Verified code and threat
Main `4d46c1d1f9c91c5fcd5961d3ad27e82c0e8e0f42`, `scripts/wheel_manifest.py::_identity`, is the shared release archive byte identity used for the wheel, source distribution and prepared wheelhouse. Current `_identity` rejects a symlink at open, reads and inspects an opened file descriptor, then checks the initial and final FD `fstat` signatures (dev, inode, size, mtime_ns, ctime_ns) for mutation during hashing. After closing the FD it performs `current=wheel.lstat()`, but compares only **dev, inode and size** against `last`. A rewrite of the *same inode* with the *same byte length* after the last `fstat`, restoring original mtime using `os.utime`, changes pathname bytes but passes the final check, because ctime is not compared there. The returned SHA256 then attests bytes no longer present at the published pathname.

Existing real tests reject inode swaps during digest and path swaps between archive metadata inspection and digest, but do **not** exercise an in-place post-fd close same-size rewrite. New test should inject at the exact second `Path.lstat`, after the opened descriptor closes, with actual filesystem writes.

## Impact and limitations
The digest mismatch can affect every `_identity` caller: wheel, sdist and dependency wheelhouse, including manual release workflow `.github/workflows/release.yml`. It can produce a false integrity claim under local concurrent mutation. Updating final pathname identity to compare `current.st_mtime_ns` and `current.st_ctime_ns` as well as dev/inode/size will detect the tested race while leaving hash bytes, digest algorithm, file lengths, manifest schema, archive metadata parser and package delivery unchanged.

Under POSIX, ctime changes after an in-place overwrite even when mtime is restored. Windows may have different `st_ctime` semantics; this test is marked POSIX only. There is no perfect atomic snapshot or protection against modifications **after** the final check, and remote filesystem timestamp behavior is not universal. No additional hash read, per-file locking or release tag publication.

## TDD target
Make a file `candidate.whl` with 4096 'A' bytes, set a known nanosecond mtime, capture its dev/inode/size/mtime/ctime. Monkeypatch `Path.lstat` exclusively when invoked on this path; at **second** invocation, write 4096 'B' bytes in place and reset `mtime_ns`. Then delegate to genuine `Path.lstat`. `_identity(candidate)` must raise `WheelManifestError(match="changed|identity")`. Assert precisely two lstat observations, the same inode/size/mtime, changed ctime and actual replacement bytes. This is a regression through actual public helper file identity, not fabricated fd metadata.

If GitHub Actions runner is delayed, preserve committed test-only SHA and document local versus remote RED accurately. Prefer proof on original production head.

## Scope
Issue #60 durable wheel publication and #53 consumer migration remain owner-gated; no tag, GitHub Release or version pin change should happen in this issue.
