# Plan: build workspace and create-only publication

Issue: #4

## Public API

Add `tf_build.workspace`:

```python
class BuildWorkspaceError(RuntimeError): ...

class BuildWorkspace:
    def __init__(self, destination: str | Path): ...
    @property
    def path(self) -> Path: ...
    @property
    def destination(self) -> Path: ...
    def publish(self) -> Path: ...
    def __enter__(self) -> BuildWorkspace: ...
    def __exit__(self, exc_type, exc, tb) -> None: ...
```

Typical use:

```python
with BuildWorkspace(output) as workspace:
    build(workspace.path)
    validate(workspace.path)
    workspace.publish()
```

## Constructor invariants

- final destination must be absent and not a symlink;
- destination parent may be created;
- physical parent is resolved once and retained;
- staging is a fresh private directory inside that physical parent;
- no corpus/TF code is invoked.

## Lifecycle

States are conceptually:

`active -> published`
or
`active -> closed_without_publish`.

- `path` is valid only while active and before successful publication;
- `publish()` atomically moves the entire staging tree to the absent destination;
- concurrent destination appearance yields `FileExistsError`;
- a failed publication leaves staging available until context exit, then cleanup removes it;
- context exit cleans unpublished staging;
- successful publication is never removed by context exit;
- repeated publication and use after close fail explicitly.

## RED-first tests

Use real filesystem operations.

1. fresh workspace creates a sibling staging directory and leaves destination absent;
2. payload published intact to destination;
3. context exit without publish cleans staging;
4. exception before publish cleans staging and leaves destination absent;
5. existing empty directory, non-empty directory, file, symlink and dangling symlink are rejected;
6. destination created after workspace construction is not clobbered;
7. repeated publish fails explicitly;
8. path access/use after context closure fails explicitly;
9. nested missing parent directories are created and resolved;
10. staging never contains bytes from a previous artifact, demonstrating stale-output prevention for create-only builds.

## Implementation

Reuse `tf_build._atomic.publish_path_no_clobber`; do not create a second rename implementation.

Use `tempfile.mkdtemp` in the resolved physical destination parent. Cleanup uses only the workspace-owned staging path.

## Exact-head gates

- focused workspace tests;
- full pytest;
- Ruff;
- strict mypy;
- Python 3.11–3.14 CI;
- adversarial review focused on races, symlinks, path ownership, cleanup, and stale state.
