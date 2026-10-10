# Research: validate read-only Text-Fabric corpora without weakening source checks

Issue: #43

## Current failure, grounded in production and actual corpus workflows

`src/tf_build/validate.py::_uncached_source_view` was introduced in PR #34 to force Text-Fabric to parse the shipped `*.tf` bodies rather than load a newer compiled `.tf/*.tfx` cache. It creates `tempfile.TemporaryDirectory(prefix=".tf-build-source-verify-", dir=directory.parent)`. When the caller's corpus directory and its parent are readable but not writable (for example an installed corpus, mounted read-only filesystem or shared system corpus), ordinary `validate_tf_artifact(..., level="selected"|"all")` now fails before inspecting data, even when the process can write to the system temporary directory.

This write requirement is not inherent in TF validation: Text-Fabric only needs a scratch workspace for compiled caches. The existing source-only view already links or copies emitted `.tf` files and validates the real TF corpus in isolation. Both `os.link` and its nonblocking/nofollow `shutil.copyfileobj` fallback handle distinct filesystem devices. `metadata` does not use this view.

## Design choice

Prefer the existing sibling temporary directory, preserving same-filesystem hardlinks and low disk overhead. If sibling stage creation fails specifically with `EACCES`, `EPERM`, or `EROFS`, retry `tempfile.TemporaryDirectory(prefix=".tf-build-source-verify-")` in the OS-configured temporary location. System temporary directories are private by default. The existing link/copy logic handles `EXDEV` between original corpus and scratch filesystem.

Do **not** retry arbitrary errors (`ENOSPC`, `ENOENT`, `ELOOP`, `ENOTDIR`, etc.), as they may indicate corruption/path races and shouldn't be masked by a fallback. If both locations fail, expose a single `ArtifactValidationError` and do not certify the artifact. Preserve full cleanup, emitted source bytes, and caller-owned binary caches. There is no new generic tempdir manager, and no change to public validation API.

## Risks and boundaries

Cross-device fallback can require a full copy of source features and additional I/O/disk; keep the fast sibling option whenever available. The destination must be private and removed on success and failure. As before, hardlinks do not yield an atomic snapshot against external concurrent in-place mutation. Avoid chmod-based CI tests because root and Windows vary; patch only the scratch-creation boundary to simulate permission denial and exercise the *real* Text-Fabric load and cache invariants.
