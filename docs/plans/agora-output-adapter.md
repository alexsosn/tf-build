# Plan: minimal Agora output adapter primitives

Issue: #8

## API

```python
class AgoraOutputError(ValueError): ...

def prepare_agora_output(root: str | Path) -> Path: ...
def optional_source_revision(revision: str) -> str | None: ...
def agora_output_path(root: str | Path, relative: str) -> Path: ...
```

- `prepare_agora_output`: return a canonical concrete existing empty directory; reject missing/file/symlink/non-empty; never create/empty/overwrite it.
- `optional_source_revision`: the host's exact empty string maps to `None`; otherwise call tf-build's full Git revision validator and return canonical lowercase 40/64 SHA; reject symbolic/abbreviated/malformed revisions. It never invents a corpus-local sentinel.
- `agora_output_path`: validate that an explicit relative POSIX artifact path is non-empty, has no absolute/drive/UNC/backslash, `.` or `..` segments, and does not equal the root-only reserved `agora-materialization.json`; reject existing symlink components and root symlinks; return path beneath canonical root. Do not create files or directories.

The plain `root` returned by `prepare_agora_output` supports Pseudepigrapha's direct output; `agora_output_path(root, "tf")` supports Coptic's nested output. Report naming/format remains producer-local.

## RED-first tests

1. valid existing empty directory accepted; no path creation/changes.
2. missing directory, regular file, symlink and non-empty directory rejected.
3. empty source revision stays explicitly absent; full SHA-1/SHA-256 canonicalize; symbolic/short revision rejected.
4. nested and direct layout paths derived inside same output root.
5. traversal, POSIX/Windows absolute, drive-relative, UNC, backslash, empty and dot paths rejected.
6. writing to reserved Agora host receipt is refused, but consumer-owned report filenames work.
7. existing symlinked output subdirectory or intermediate component rejected without touching target.
8. validation is local-only; no source acquisition or host publication.

## Gates

Tests before production code; exact-head Python 3.11–3.14 pytest/Ruff/mypy; separate adversarial review against current Agora host and two registered consumer manifests before merge. Keep API minimal enough that neither materializer must change layout.
