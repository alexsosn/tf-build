# Plan: Git source identity and local checkout verification

Issue: #2

## Public API

Create `tf_build.source` with:

```python
class GitSourceError(RuntimeError): ...

@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    path: Path
    repository_root: Path
    revision: str
    object_format: Literal["sha1", "sha256"]

def validate_git_revision(revision: str) -> str: ...
def verify_git_source(
    source: str | Path,
    *,
    expected_revision: str | None = None,
) -> SourceSnapshot: ...
```

A lower-level command runner and resolution helpers remain private until a second public use appears.

## Invariants

- `revision` is canonical lowercase full SHA-1/SHA-256 hexadecimal.
- `path` and `repository_root` are absolute canonical paths.
- `path` is within `repository_root`.
- the repository is a non-bare working tree;
- working-tree status is clean, including untracked files and submodule changes;
- when `expected_revision` is supplied it equals resolved `HEAD`;
- verification performs no network operation.

## Failure policy

Raise `GitSourceError` for:

- missing/non-directory source;
- non-Git directory or bare repository;
- unsupported/ambiguous revision syntax;
- Git inspection failure;
- expected/resolved mismatch;
- dirty worktree;
- unexpected Git object-id format.

Do not silently downgrade any condition to a warning.

## RED tests

Before production implementation, add tests using real temporary Git repositories for:

1. 40- and 64-hex lexical validation and lowercase normalization;
2. symbolic/abbreviated/invalid revisions rejected;
3. clean SHA-1 checkout accepted;
4. clean SHA-256 checkout accepted when supported by the installed Git;
5. mismatch rejected;
6. tracked, staged and untracked dirtiness rejected;
7. non-Git directory rejected;
8. source subdirectory returns both selected path and repository root.

The RED run must fail because `tf_build.source` does not exist, not because the fixture is broken.

## Implementation

Use `subprocess.run(..., check=True, capture_output=True, text=True)` with local `git -C <path>` commands. Resolve `HEAD`, top-level path, working-tree status and bare/worktree state. Keep command construction internal and deterministic.

## GREEN / exact-head gates

- focused source tests;
- full pytest suite;
- Ruff;
- strict mypy;
- CI on Python 3.11–3.14;
- exact-head independent adversarial review grounded in the ORAEC/Coptic contracts and real Git behavior.
