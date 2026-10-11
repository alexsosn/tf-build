# Research: bounded, unambiguous package identity in release manifest (#72)

## Real code and pathways
At main `0cf4b8c5701e9a6cfb5dfc0bcf07b1b235cb595b`, both `.github/workflows/ci.yml` and `.github/workflows/release.yml` invoke `scripts/wheel_manifest.py` after building a noneditable wheel plus an emitted sdist. Its role is to bind real wheel/sdist SHA-256 bytes, source Git SHA and package/version identity. Actual CI `38138835978` passed 5/5 quality/distribution jobs for this source, so the defect is not a presently broken legitimate build.

In `build_wheel_manifest`, the code does `BytesParser().parsebytes(archive.read(metadata_path))`; `zipfile.ZipFile.read` decompresses all metadata without an upper bound. The sdist path instead rejects PKG-INFO if the tar member exceeds 1 MiB, then reads at most 1 MiB + 1. Neither path checks `message.defects` or `get_all` multiplicity. A first, plausible `Name` or `Version` followed by a conflicting duplicate succeeds. Neither checks required `Metadata-Version`.

The current PyPA core metadata specification (https://packaging.python.org/en/latest/specifications/core-metadata/, currently version 2.6) requires exactly one `Metadata-Version`, `Name`, `Version` and defines `email.parser` under `compat32` as practical parsing standard. Keeping parsed raw values for identity comparison preserves the existing strict `tf-build` and exact version binding (do not silently normalize cross-package names at this release gate).

## Threat model and boundaries
ZIP compressed bomb masquerading as a small wheel `METADATA` can allocate huge memory; duplicated metadata names let a ZIP or tarball with conflicting identities be manifested as trusted. Output already includes a byte-level SHA256, but a hash proves integrity of the bytes not semantic identity. No candidate code execution is needed to fix. Reject ZIP member `file_size` beyond 1 MiB and read at most 1 MiB + 1 bytes while streaming, without extracting; reject malformed or non-singleton required identity headers for both artifacts. Existing tests fabricate actual ZIP and tar.gz files, and can assert failures before implementation.

Non-goals: full Core Metadata syntax/version/PEP440 validation, validating every WHEEL tag, proving RECORD correctness, generalized archive scanner, changing release approval or protected tag policy. Durable published assets are still owner-controlled under #60; ORAEC consumer #53 remains separate.
