# Research: deterministic raw artifact identity

Issue: #7

## Evidence from real consumers

- CopticScriptorium-TF writer removes Text-Fabric's volatile `@dateWritten` header before publishing `.tf` feature bytes. These actual published bytes can then be raw-hashed.
- TLHdig-TF `programs/tlhdig/build_manifest.py` currently skips `@dateWritten` when hashing TF files, and its own reproducibility research explicitly distinguishes that **canonicalized/logical identity** from byte-equality of shipped files. Its later raw-byte proof independently compares ordinary SHA-256 hashes.
- Text-Fabric `Fabric.load` may generate derived `.tf/` cache entries; cache contents depend on environment and are not shipped source features.

## Decision

`tf-build` implements a **raw-byte** tree fingerprint, independent of TF feature semantics. There is no hidden normalization or pseudo-timestamp policy. A caller who requires deterministic raw identity must make the underlying bytes deterministic before fingerprinting.

The fingerprint covers all regular shipped files recursively, not just `.tf`, including config, provenance, LICENSE and README. Exclusions are deliberately narrow: Text-Fabric `.tf/` compiled caches and exactly one optional caller-named manifest file to prevent self-reference. Excluded files are explicitly outside the integrity claim.

## Algorithm `tf-build-tree-sha256-v1`

- Resolve a concrete root directory; reject a symlink root.
- Traverse filesystem entries without following symlinks. Reject symlinks/nonregular entries (including suspicious `.tf` cache paths).
- Ignore only real directories named `.tf` and their descendants (derived compiled caches).
- For every other regular file, compute SHA-256 over exact file bytes; retain its POSIX-relative path and byte count.
- Sort relative paths by their UTF-8 bytes (no silent Unicode normalization).
- Aggregate SHA-256 begins with the versioned ASCII domain prefix `tf-build-tree-sha256-v1\0` and, for each record, hashes an unsigned 8-byte big-endian path-byte length, the UTF-8 path bytes, an unsigned 8-byte big-endian size, and the raw 32-byte SHA-256 file digest.
- Digest strings use lowercase `sha256:<64 hex>`.

Length framing removes ambiguity from unusual but legal filenames. File size and byte digest are both committed to the tree identity. Hardlinks are distinct logical names and both are included.

## Concurrent mutation

A fingerprint of a concurrently changing directory is not an atomic snapshot. After opening a file, compare identity/size/mtime before and after streaming where supported; these checks reduce accidental races but do not justify a claim of adversarial race-free snapshotting. Expected use is completed, private `BuildWorkspace` staging before publish.

## Non-goals

- TF feature parsing or semantic equivalence;
- canonicalized timestamp/header hashes;
- signing, release validation or declaring successful build gates;
- an arbitrary ignore-glob DSL that permits unnoticed omitted shipped files;
- reproducing source acquisition identity;
- automatically rewriting source `.tf` files.
