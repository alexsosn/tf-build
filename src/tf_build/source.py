"""Immutable Git source identity and local checkout verification."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
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


def fetch_git_source(
    repository: str,
    destination: str | Path,
    *,
    revision: str,
) -> SourceSnapshot:
    """Acquire one immutable Git commit and publish a verified clean checkout."""
    requested_revision = validate_git_revision(revision)
    if not isinstance(repository, str) or not repository.strip():
        raise GitSourceError("Git repository locator must be a non-empty string")

    target = Path(destination)
    if target.is_symlink():
        raise GitSourceError(f"destination must not be a symlink: {target}")

    target_preexisted = target.exists()
    if target_preexisted:
        if not target.is_dir():
            raise GitSourceError(
                f"destination exists and is not a directory: {target}"
            )
        if any(target.iterdir()):
            raise GitSourceError(f"destination is not empty: {target}")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GitSourceError(
            f"could not create destination parent: {target.parent}"
        ) from exc

    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{target.name}.tf-build-",
            dir=target.parent,
        )
    )
    removed_preexisting = False

    try:
        init_args = ["init", "--quiet"]
        if len(requested_revision) == 64:
            init_args.append("--object-format=sha256")
        _run_git(staging, *init_args)
        _run_git(staging, "remote", "add", "origin", repository)
        _run_git(
            staging,
            "fetch",
            "--depth",
            "1",
            "origin",
            requested_revision,
        )
        _run_git(staging, "checkout", "--detach", "FETCH_HEAD")

        snapshot = verify_git_source(
            staging,
            expected_revision=requested_revision,
        )

        if target_preexisted:
            target.rmdir()
            removed_preexisting = True

        staging.replace(target)
        published = target.resolve(strict=True)
        return SourceSnapshot(
            path=published,
            repository_root=published,
            revision=snapshot.revision,
            object_format=snapshot.object_format,
        )
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        if target_preexisted and removed_preexisting and not target.exists():
            target.mkdir(parents=False, exist_ok=False)
        raise


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
    "fetch_git_source",
    "validate_git_revision",
    "verify_git_source",
]
