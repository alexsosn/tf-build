# Plan: pinned staged Git source acquisition

Issue: #3

## Public API

Extend `tf_build.source` with:

```python
def fetch_git_source(
    repository: str,
    destination: str | Path,
    *,
    revision: str,
) -> SourceSnapshot: ...
```

The function is create-only. It returns the same verified `SourceSnapshot` contract as `verify_git_source`.

## Preconditions

Before invoking Git:

- `revision` passes `validate_git_revision`;
- repository locator is a non-empty string;
- destination is not a symlink;
- existing destination is an empty physical directory;
- existing non-directory/non-empty destinations fail closed.

## Acquisition algorithm

1. validate inputs;
2. create destination parent as needed;
3. create a private staging directory beside the destination;
4. `git init --quiet` with object format derived from revision length;
5. `git remote add origin <repository>`;
6. `git fetch --depth 1 origin <revision>`;
7. `git checkout --detach FETCH_HEAD`;
8. verify staging with `verify_git_source(..., expected_revision=revision)`;
9. if caller supplied an empty destination, remove it immediately before publication;
10. rename/replace staging onto destination;
11. return a snapshot whose selected path/root point to the published destination.

On any failure, remove staging. Restore a caller-supplied empty destination if it was removed but publication did not complete.

## RED-first tests

Use local repositories; no network and no mocked success path.

Required cases:

- nonexistent destination succeeds for SHA-1;
- pre-existing empty destination succeeds;
- SHA-256 source/revision succeeds with SHA-256 staging;
- symbolic/abbreviated revision is rejected before Git acquisition;
- empty repository locator is rejected before Git acquisition;
- symlink (including dangling), file and non-empty destinations are rejected;
- acquisition failure leaves no destination when none existed;
- acquisition failure preserves a pre-existing empty destination;
- resulting checkout is detached, exact, clean and verified.

Failure injection may mock the private Git runner only for cleanup behavior that cannot be induced deterministically without coupling tests to a remote.

## Exact-head gates

- focused acquisition tests;
- all source verification tests;
- full pytest;
- Ruff and strict mypy;
- CI Python 3.11–3.14;
- independent adversarial review, including path-state and SHA-256 behavior.
