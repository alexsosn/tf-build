"""Immutable Git source identity and local checkout verification."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_REVISION_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")


class GitSourceError(RuntimeError):
    """Raised when an immutable local Git source cannot be verified."""


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """Identity of a verified clean local Git working tree."""

    path: Path
    repository_root: Path
    revision: str
    object_format: Literal["sha1", "sha256"]


def validate_git_revision(revision: str) -> str:
    """Return a canonical full Git commit id or reject ambiguous syntax."""
    if not isinstance(revision, str) or _REVISION_RE.fullmatch(revision) is None:
        raise GitSourceError(
            "Git revision must be a full 40- or 64-hex immutable commit id"
        )
    return revision.lower()


def _run_git(source: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        command = " ".join(args)
        raise GitSourceError(
            f"Git inspection failed while running {command!r} for {source}"
        ) from exc
    return result.stdout.strip()


def _canonical_source(source: str | Path) -> Path:
    requested = Path(source)
    try:
        path = requested.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise GitSourceError(f"source directory does not exist: {requested}") from exc
    if not path.is_dir():
        raise GitSourceError(f"source path is not a directory: {path}")
    return path


def verify_git_source(
    source: str | Path,
    *,
    expected_revision: str | None = None,
) -> SourceSnapshot:
    """Verify a clean local Git working tree without contacting any remote."""
    expected = (
        None
        if expected_revision is None
        else validate_git_revision(expected_revision)
    )
    path = _canonical_source(source)

    inside_work_tree = _run_git(path, "rev-parse", "--is-inside-work-tree")
    if inside_work_tree != "true":
        raise GitSourceError(f"source is not a Git working tree: {path}")

    root_text = _run_git(path, "rev-parse", "--show-toplevel")
    try:
        repository_root = Path(root_text).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise GitSourceError(
            f"Git reported an invalid working-tree root for {path}: {root_text!r}"
        ) from exc

    if path != repository_root and repository_root not in path.parents:
        raise GitSourceError(
            f"source path is outside the Git working-tree root: {path}"
        )

    revision = validate_git_revision(
        _run_git(path, "rev-parse", "--verify", "HEAD^{commit}")
    )
    if expected is not None and revision != expected:
        raise GitSourceError(
            f"Git revision mismatch: expected {expected}, resolved {revision}"
        )

    status = _run_git(
        path,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if status:
        raise GitSourceError(f"Git working tree is dirty: {repository_root}")

    object_format: Literal["sha1", "sha256"] = (
        "sha1" if len(revision) == 40 else "sha256"
    )
    return SourceSnapshot(
        path=path,
        repository_root=repository_root,
        revision=revision,
        object_format=object_format,
    )


__all__ = [
    "GitSourceError",
    "SourceSnapshot",
    "validate_git_revision",
    "verify_git_source",
]
