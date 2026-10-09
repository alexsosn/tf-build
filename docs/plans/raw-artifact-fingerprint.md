# Plan: raw artifact tree fingerprint

Issue: #7

## Initial API

```python
class FingerprintError(ValueError): ...

@dataclass(frozen=True, slots=True)
class FileFingerprint:
    path: str
    size: int
    sha256: str

@dataclass(frozen=True, slots=True)
class TreeFingerprint:
    algorithm: str
    digest: str
    files: tuple[FileFingerprint, ...]

def fingerprint_tree(root: str | Path, *, manifest_path: str | None = None) -> TreeFingerprint: ...
```

No dependency on `tf_build.validate` is required. The output can later be attached to a separate provenance/release manifest but must not be mistaken for proof that the source snapshot, converter or scholarly checks were valid.

## RED-first tests

1. same tree always produces same digest, independent of creation order;
2. editing file bytes changes file digest and root digest even when lengths match;
3. adding/removing/renaming a file changes tree identity;
4. nested files, empty files and a truly empty tree are deterministic;
5. non-TF shipped files contribute to identity;
6. derived `.tf/` caches are excluded, but any other name is included;
7. explicitly named manifest file is excluded to avoid recursive hashing; nonexcluded sibling manifests remain in identity;
8. symlinked directory/file/root rejected without following links;
9. FIFO/nonregular entries rejected where platform supports them;
10. tree hash framing has an independent oracle and cannot suffer path concatenation ambiguity;
11. invalid manifest path (absolute, traversal, backslash/drive-relative) rejected;
12. no hidden TF normalization: header byte changes alter raw hash.

## Implementation

Standard library `hashlib`, `os.scandir`, `stat` and streamed reads only. Use no arbitrary ignore set and no JSON sidecars in the TF dataset. Return immutable typed objects; canonical serialization may be added only when a real consumer needs it.

## Review / integration

Test with synthetic artifact trees and one real consumer-style TF tree (regular `.tf` files plus license and `.tf/` cache). Run pytest/Ruff/strict mypy across Python 3.11–3.14. Independent adversarial review must challenge symlink handling, path framing, excluded paths, mutation detection and whether raw byte claims match the implementation.

Do not merge before exact-head CI and review pass.
