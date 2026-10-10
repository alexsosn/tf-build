# Plan: public low-level atomic no-clobber API

Issue #54.

1. Research the existing `_atomic.py` syscall contracts and both real consumers (`BuildWorkspace` and ORAEC's host-owned Agora outer publication).
2. **RED-first** write `tests/test_publish.py` exercising the proposed public `tf_build.publish.publish_path_no_clobber` API with actual OS directory/file operations:
   - staged directory -> absent final output success, preserving complete nested contents;
   - create an **empty competing directory** after preparing stage, record inode and require `FileExistsError`, stage preserved and competitor inode unchanged;
   - nonempty destination/file/symlink all fail without altering either source or target;
   - successful regular file publish works when target is absent.
   Missing public API should fail at collection/import against current main while existing private producer tests remain green.
3. Implement the thinnest public `tf_build.publish` facade accepting `str | Path`, delegating to `_atomic.publish_path_no_clobber(Path(...), Path(...))`; no new fallback/syscalls or speculative path ownership policy. Make `BuildWorkspace.publish` import the new public API.
4. Add usage docs explicitly distinguishing `BuildWorkspace`'s lifecycle, low-level call's absence of staging/cleanup/certification and the external Oraec host pattern.
5. On exact head run Ruff, mypy and pytest on Python 3.11–3.14. Perform a skeptical independent review against the real RED evidence, existing platform implementation and both consumer contracts. Merge only with four exact-head green jobs; leave ORAEC dependency migration separate.
