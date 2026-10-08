# Plan: deterministic exact-byte TF artifact manifest

Issue: #7

## Public API

Add `tf_build.fingerprint`:

```python
ArtifactFile(
    path: str,
    bytes: int,
    sha256: str,
)

ArtifactFingerprint(
    schema: int,
    algorithm: str,
    digest: str,
    files: tuple[ArtifactFile, ...],
)

fingerprint_tf_artifact(path: str | Path) -> ArtifactFingerprint
verify_tf_artifact(path: str | Path, expected: ArtifactFingerprint) -> None
write_tf_artifact_manifest(
    path: str | Path,
    fingerprint: ArtifactFingerprint,
) -> Path
```

`ArtifactFingerprint.to_dict()/to_json()` provide deterministic schema-1 serialization.

Use `ArtifactFingerprintError(RuntimeError)` for unsafe/unreadable artifact state or verification mismatch.

Canonical constants:

- schema: `1`;
- algorithm: `tf-build-artifact-tree-v1`;
- manifest filename: `tf-build-manifest.json`;
- per-file and aggregate hash: SHA-256.

## Enumeration

1. reject a symlinked/non-directory root;
2. recursively inspect entries;
3. skip any path below a component named `.tf`;
4. skip only root `tf-build-manifest.json`;
5. reject every included symlink or non-regular entry;
6. convert included relative paths to strict UTF-8 POSIX strings;
7. sort by UTF-8 path bytes.

Do not expose arbitrary glob exclusions in schema 1; arbitrary omissions would weaken closed-world identity.

## Per-file hashing

For each included file:

- verify it is still a regular non-symlink entry immediately before open;
- stream raw bytes through SHA-256;
- record exact streamed byte count;
- if the entry disappears/changes type during access, raise;
- emit lowercase `sha256:<hex>`.

Avoid reading entire large artifacts into RAM.

## Aggregate hashing

Initialize SHA-256 with:

`b"tf-build-artifact-tree-v1\\0"`

For every sorted file record append:

- unsigned 8-byte big-endian UTF-8 path length;
- path bytes;
- unsigned 8-byte big-endian byte count;
- raw 32-byte file digest.

Return `sha256:<hex>`.

## Manifest validation

Dataclass construction must validate:

- exact schema/algorithm constants;
- strict portable relative file paths;
- non-negative integer byte counts, rejecting bool;
- canonical SHA-256 strings;
- unique, correctly sorted paths;
- aggregate digest matches the file records.

A parsed/constructed manifest cannot claim an arbitrary digest inconsistent with its own file table.

## Verification

`verify_tf_artifact()` recomputes the current artifact and compares the full immutable fingerprint.

On mismatch, error text should identify at least the first class of difference:

- missing file;
- unexpected file;
- changed file size/digest;
- aggregate mismatch.

Do not merely return a boolean; callers must not accidentally ignore a failed verification.

## Manifest writing

The writer target is exactly `<artifact-root>/tf-build-manifest.json`.

Requirements:

- root must already exist and be safe;
- serialize deterministic UTF-8 JSON;
- write to a fresh sibling temporary file;
- fsync is not required in schema 1, but partial target content must never be exposed;
- atomically replace only the canonical manifest file; this is file replacement, not directory publication;
- reject a symlinked manifest target;
- recomputing the artifact before/after writing yields the same artifact digest because the canonical manifest is excluded.

## RED-first tests

Use real temporary files; TF itself is unnecessary for the hashing primitive except one integration fixture may use a tiny TF tree.

At minimum:

1. same tree fingerprints byte-for-byte identically on repeated calls;
2. changing one byte changes that file digest and aggregate digest;
3. adding/removing/renaming a file changes identity;
4. nested files participate with POSIX-relative paths;
5. path ordering is deterministic independent of creation order;
6. auxiliary non-`.tf` files participate;
7. Text-Fabric compiled `.tf/` cache contents do not affect identity;
8. root `tf-build-manifest.json` does not affect identity;
9. a nested file also named `tf-build-manifest.json` **does** participate;
10. symlinked file/root fail closed without dereferencing target;
11. non-regular entry fails where the platform supports creating one safely in tests;
12. invalid/non-portable manifest paths and invalid digest strings are rejected;
13. aggregate digest is independently recomputed from known file records;
14. empty tree has one deterministic domain-separated identity;
15. deterministic JSON has sorted keys and one trailing newline;
16. verification succeeds for the original tree and fails diagnostically for missing/unexpected/changed files;
17. writing the canonical manifest is atomic enough that recomputed fingerprint is unchanged and the JSON equals `to_json()`;
18. symlinked canonical manifest target is rejected.

## Integration

After #6 is available, add one composition test on a tiny validated TF artifact:

build -> validate -> fingerprint -> write manifest -> verify -> publish via BuildWorkspace.

This integration can be in #7 if #6 is merged first; otherwise it is a follow-up. The fingerprint module itself remains independent of Text-Fabric imports.

## Exact-head gates

Full pytest, Ruff, strict mypy, Python 3.11-3.14 CI, then logically independent adversarial review focused on closed-world enumeration, path ambiguity, symlinks, exclusion policy, digest framing, large-file streaming, manifest recursion, and mismatch diagnostics.
