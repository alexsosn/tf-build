# Plan: reject unstable artifact file paths while fingerprinting (#82)

1. Record source-backed research and this plan before behavior/test changes.
2. RED-first test via public `fingerprint_tree`: use `monkeypatch` on SHA256 `update` to synchronously replace `otype.tf` with a different same-length inode after the original opened stream was read. Expect `FingerprintError`. A second test mutates the same open inode, restores its mtime_ns and verifies `ctime_ns` guard rejects it. Keep positive oracle for unchanged real source bytes. Run tests-only GitHub CI and preserve an actual RED pytest result before implementation.
3. Implement minimal robust checks in `_file_identity`: compare ctime_ns in pre/post fstat; after hashing inspect `path.lstat`, require regular mode and matching opened dev/inode, size, mtime_ns and ctime_ns. Wrap lstat failures in `FingerprintError`, never return a digest for a disappeared path. Preserve nofollow/nonblocking flags and existing digest.
4. Run exact-head Ruff, mypy, pytest on Python 3.11–3.14 and real wheel/sdist distribution/installed/offline CI. Review the frozen diff independently from an adversarial viewpoint, including POSIX safety and residual non-atomic tree limitation; record review as GitHub COMMENT tied to exact SHA.
5. Merge only after all five jobs pass and skeptic review succeeds; no owner release actions or ORAEC migration.
