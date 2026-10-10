"""Minimal host-owned Agora output and source handoff helpers.

Agora owns sandboxing, acquisition and final publication. These functions only
validate local preconditions and return safe paths; they do not run converters.
"""

from __future__ import annotations

from pathlib import Path, PureWindowsPath

from .source import GitSourceError, validate_git_revision

_RESERVED_RECEIPT = "agora-materialization.json"


class AgoraOutputError(ValueError):
    """A caller-supplied Agora staging or source handoff is invalid."""


def _root_directory(root: str | Path) -> Path:
    requested = Path(root)
    if requested.is_symlink():
        raise AgoraOutputError(f"Agora output root is a symlink: {requested}")
    if not requested.is_dir():
        raise AgoraOutputError(f"Agora output must be an existing directory: {requested}")
    try:
        return requested.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AgoraOutputError(f"could not resolve Agora output directory: {requested}") from exc


def prepare_agora_output(root: str | Path) -> Path:
    """Preflight an existing host-owned empty output root without changing it."""
    directory = _root_directory(root)
    try:
        if any(directory.iterdir()):
            raise AgoraOutputError(
                f"Agora output must be empty before conversion: {directory}"
            )
    except OSError as exc:
        raise AgoraOutputError(f"cannot inspect Agora output: {directory}") from exc
    return directory


def optional_source_revision(revision: str) -> str | None:
    """Interpret Agora's empty user-local revision without inventing a Git ID."""
    if revision == "":
        return None
    try:
        return validate_git_revision(revision)
    except GitSourceError as exc:
        raise AgoraOutputError(f"invalid Agora source revision: {exc}") from exc


def _relative_path(relative: str) -> tuple[str, ...]:
    if (
        not isinstance(relative, str)
        or not relative
        or relative.startswith("/")
        or "\\" in relative
        or bool(PureWindowsPath(relative).drive)
        or any(segment in {"", ".", ".."} for segment in relative.split("/"))
        or "\x00" in relative
    ):
        raise AgoraOutputError("Agora artifact path must be a safe relative POSIX path")

    if relative == _RESERVED_RECEIPT:
        raise AgoraOutputError(f"Agora artifact path is reserved by the host: {relative}")
    return tuple(relative.split("/"))


def agora_output_path(root: str | Path, relative: str) -> Path:
    """Resolve an output-relative generated artifact path without creating it.

    This checks symlinked existing path components but does not replace Agora's
    sandbox or provide an atomic defense against concurrent directory mutation.
    """
    directory = _root_directory(root)
    components = _relative_path(relative)
    candidate = directory
    for part in components:
        candidate = candidate / part
        if candidate.is_symlink():
            raise AgoraOutputError(f"Agora artifact path contains symlink: {candidate}")
    return candidate


__all__ = [
    "AgoraOutputError",
    "agora_output_path",
    "optional_source_revision",
    "prepare_agora_output",
]
