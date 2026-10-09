"""Versioned raw-byte identities for complete generated artifact trees."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

ALGORITHM = "tf-build-tree-sha256-v1"
_PREFIX = b"tf-build-tree-sha256-v1\x00"
_CHUNK = 1024 * 1024


class FingerprintError(ValueError):
    """A generated artifact cannot be fingerprinted safely."""


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    """Identity of exact bytes at one artifact-relative filename."""

    path: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class TreeFingerprint:
    """Closed-world raw-byte identity (excluding documented derived material)."""

    algorithm: str
    digest: str
    files: tuple[FileFingerprint, ...]


def _manifest_name(name: str | None) -> str | None:
    if name is None:
        return None
    if (
        not isinstance(name, str)
        or not name
        or name.startswith("/")
        or "\\" in name
        or bool(PureWindowsPath(name).drive)
        or any(part in {"", ".", ".."} for part in name.split("/"))
        or "\x00" in name
    ):
        raise FingerprintError("manifest exclusion must be a safe relative POSIX path")
    return name


def _files(root: Path, manifest: str | None) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []

    def walk(directory: Path, prefix: str) -> None:
        try:
            with os.scandir(directory) as entries:
                candidates = list(entries)
        except OSError as exc:
            raise FingerprintError(f"cannot enumerate artifact directory {directory}") from exc
        for item in candidates:
            relative = f"{prefix}/{item.name}" if prefix else item.name
            path = Path(item.path)
            try:
                if item.is_symlink():
                    raise FingerprintError(f"artifact contains symlink: {relative}")
                if item.is_dir(follow_symlinks=False):
                    if item.name == ".tf":
                        # Compiled Text-Fabric binary caches, not source features.
                        continue
                    if relative == manifest:
                        raise FingerprintError(
                            f"manifest exclusion names an artifact directory: {relative}"
                        )
                    walk(path, relative)
                elif item.is_file(follow_symlinks=False):
                    if relative != manifest:
                        files.append((relative, path))
                else:
                    raise FingerprintError(f"artifact contains non-regular entry: {relative}")
            except OSError as exc:
                raise FingerprintError(f"cannot inspect artifact entry {relative}") from exc

    walk(root, "")
    try:
        files.sort(key=lambda pair: pair[0].encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise FingerprintError("artifact contains a filename not representable as UTF-8") from exc
    return files


def _file_identity(name: str, path: Path) -> FileFingerprint:
    # O_NOFOLLOW protects the final path component on supporting platforms.
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise FingerprintError(f"cannot open regular artifact file {name}") from exc

    digest = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(fd, "rb") as stream:
            first = os.fstat(stream.fileno())
            if not stat.S_ISREG(first.st_mode):
                raise FingerprintError(f"artifact file became non-regular: {name}")
            while block := stream.read(_CHUNK):
                digest.update(block)
                size += len(block)
            last = os.fstat(stream.fileno())
            if (
                size != last.st_size
                or (first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns)
                != (last.st_dev, last.st_ino, last.st_size, last.st_mtime_ns)
            ):
                raise FingerprintError(f"artifact file changed during hashing: {name}")
    except OSError as exc:
        raise FingerprintError(f"could not read artifact file {name}") from exc

    return FileFingerprint(
        path=name,
        size=size,
        sha256="sha256:" + digest.hexdigest(),
    )


def fingerprint_tree(
    root: str | Path,
    *,
    manifest_path: str | None = None,
) -> TreeFingerprint:
    """Hash exact bytes of every shipped regular file in a completed artifact.

    Only derived `.tf/` compiled-cache directories and the optional named
    manifest file are outside this fingerprint. This is not an atomic snapshot
    if another process is modifying the tree concurrently.
    """
    manifest = _manifest_name(manifest_path)
    directory = Path(root)
    if directory.is_symlink():
        raise FingerprintError(f"artifact root is a symlink: {directory}")
    if not directory.is_dir():
        raise FingerprintError(f"artifact root is not a directory: {directory}")

    records = tuple(_file_identity(name, path) for name, path in _files(directory, manifest))
    aggregate = hashlib.sha256()
    aggregate.update(_PREFIX)
    for item in records:
        encoded = item.path.encode("utf-8")
        aggregate.update(len(encoded).to_bytes(8, "big"))
        aggregate.update(encoded)
        aggregate.update(item.size.to_bytes(8, "big"))
        aggregate.update(bytes.fromhex(item.sha256.removeprefix("sha256:")))
    return TreeFingerprint(
        algorithm=ALGORITHM,
        digest="sha256:" + aggregate.hexdigest(),
        files=records,
    )


__all__ = [
    "ALGORITHM",
    "FileFingerprint",
    "FingerprintError",
    "TreeFingerprint",
    "fingerprint_tree",
]
