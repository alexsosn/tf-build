# Research: completed create-only release manifest publication (#86)

## Reproducible defect in production
On main `e159196c43517ce9855f6610c11d2952a662f4c5`, `scripts/wheel_manifest.py::write_wheel_manifest` calls `path.open("x",encoding="utf-8")` before `json.dumps(record,sort_keys=True,indent=2)` and directly writes output to the final `wheel-manifest.json` pathname. A non-JSON-serializable value provably raises `TypeError` **after** destination creation, leaving a zero-byte final file. An I/O error during writing similarly leaves a partial final file. CI uses this file as evidence binding the wheel, sdist and wheelhouse hashes, including the manual `.github/workflows/release.yml` workflow. A truncated final manifest invalidates provenance and prevents a clean rerun because existing output is rejected.

## Required unchanged contract
Return type None, canonical JSON `json.dumps(record,sort_keys=True,indent=2)+"\\n"`, create-only destination semantics, do not replace an existing manifest (including a symlink or directory). Release publication/tag remains owner controlled. This script can run standalone in Actions without importing the installed `tf_build` package, so do not import private package `_atomic` into it. Keep schema, wheel identity hashing, zip/tar source metadata checks, and release workflow unchanged.

## Minimal reliable filesystem strategy
Compute and encode canonical JSON before creating any output. Create a private sibling temporary regular file using `tempfile.mkstemp` in the same destination directory, write exact UTF-8 bytes, `flush` and `os.fsync` the file descriptor. Atomically **create** the destination via `os.link(staging,destination)` with no replace; `FileExistsError` on a competing path must preserve the competing bytes. Always unlink the private temp path after success/failure, even if write/flush/fsync/link raises. Hardlink publication requires same filesystem (enforced by adjacent staging) and filesystem hardlink support; an unsupported filesystem fails closed rather than falling back to non-atomic replacement. `os.link` is supported on Linux/Windows in CPython on supporting filesystems. A crash between successful link and temp unlink may leave a private staging hardlink; it does **not** leave incomplete final evidence. Durability after host power failure additionally requires directory fsync, which this scope does not guarantee; this is complete-data publication atomicity, not universal crash-durability.

## Deterministic adverse tests and acceptance
Use genuine filesystem directories and public function `write_wheel_manifest`:
1. An unserializable record triggers TypeError but leaves no destination and no temporary children. This is a guaranteed RED result against current code.
2. Inject `OSError` at `os.fsync`, require no final manifest and no leaked staging files. This exercises the new write/flush boundary and is also RED against old direct-write function (which calls no fsync).
3. Inject competing regular destination just before `os.link`, require FileExistsError and byte-for-byte preservation of competitor. Old direct open fails test because no link is attempted.
4. Verify valid output remains exact canonical JSON and repeat write fails without mutation; an existing symlink must not be followed/replaced.

Adversarial review must inspect actual code and test behavior, path races, cleanup and the exact-head Python matrix + distribution logs. No release tag/assets or consumer pin changes.
