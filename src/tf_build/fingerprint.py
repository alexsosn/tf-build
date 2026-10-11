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
                    if relative == manifest:
                        raise FingerprintError(
                            f"manifest exclusion names an artifact directory: {relative}"
                        )
                    if item.name == ".tf":
                        # Compiled Text-Fabric binary caches, not source features.
                        continue
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


def _file_identity(
    name: str, path: Path, *, directory_fd: int | None = None
) -> FileFingerprint:
    # O_NOFOLLOW protects the final path component on supporting platforms.
    # A regular file can be swapped for a FIFO after scandir; on POSIX a
    # blocking read-only open would hang before fstat could reject the FIFO.
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    if os.name == "posix":
        nonblocking = getattr(os, "O_NONBLOCK", None)
        if nonblocking is None:
            raise FingerprintError("POSIX nonblocking file open is unavailable")
        flags |= nonblocking
    try:
        fd = (
            os.open(path.name, flags, dir_fd=directory_fd)
            if directory_fd is not None
            else os.open(path, flags)
        )
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
                or (
                    first.st_dev, first.st_ino, first.st_size,
                    first.st_mtime_ns, first.st_ctime_ns,
                )
                != (
                    last.st_dev, last.st_ino, last.st_size,
                    last.st_mtime_ns, last.st_ctime_ns,
                )
            ):
                raise FingerprintError(f"artifact file changed during hashing: {name}")
        # An open file can remain unchanged after its pathname is replaced.
        # Confirm the current artifact still names the bytes just hashed.
        current = (
            os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
            if directory_fd is not None
            else path.lstat()
        )
        if (
            not stat.S_ISREG(current.st_mode)
            or (
                current.st_dev, current.st_ino, current.st_size,
                current.st_mtime_ns, current.st_ctime_ns,
            )
            != (
                last.st_dev, last.st_ino, last.st_size,
                last.st_mtime_ns, last.st_ctime_ns,
            )
        ):
            raise FingerprintError(f"artifact file changed during hashing: {name}")
    except OSError as exc:
        raise FingerprintError(f"could not read artifact file {name}") from exc

    return FileFingerprint(
        path=name,
        size=size,
        sha256="sha256:" + digest.hexdigest(),
    )


def _anchored_files(root: Path, manifest: str | None) -> list[FileFingerprint]:
    """Fingerprint a POSIX artifact below nofollow-pinned directory descriptors."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory_flag is None:
        raise FingerprintError("POSIX nofollow directory traversal is unavailable")
    flags = os.O_RDONLY | nofollow | directory_flag | getattr(os, "O_CLOEXEC", 0)
    records: list[FileFingerprint] = []

    def walk(directory_fd: int, prefix: str) -> None:
        try:
            with os.scandir(directory_fd) as entries:
                candidates = list(entries)
        except OSError as exc:
            raise FingerprintError(
                f"cannot enumerate artifact directory {prefix or root}"
            ) from exc

        for item in candidates:
            relative = f"{prefix}/{item.name}" if prefix else item.name
            try:
                if item.is_symlink():
                    raise FingerprintError(f"artifact contains symlink: {relative}")
                if item.is_dir(follow_symlinks=False):
                    if relative == manifest:
                        raise FingerprintError(
                            f"manifest exclusion names an artifact directory: {relative}"
                        )
                    if item.name == ".tf":
                        continue
                    try:
                        child_fd = os.open(item.name, flags, dir_fd=directory_fd)
                    except OSError as exc:
                        raise FingerprintError(
                            f"cannot open regular artifact directory: {relative}"
                        ) from exc
                    try:
                        first = os.fstat(child_fd)
                        if not stat.S_ISDIR(first.st_mode):
                            raise FingerprintError(
                                f"artifact directory became non-directory: {relative}"
                            )
                        walk(child_fd, relative)
                        last = os.fstat(child_fd)
                        current = os.stat(
                            item.name, dir_fd=directory_fd, follow_symlinks=False
                        )
                        if (
                            not stat.S_ISDIR(current.st_mode)
                            or (first.st_dev, first.st_ino)
                            != (last.st_dev, last.st_ino)
                            or (current.st_dev, current.st_ino)
                            != (last.st_dev, last.st_ino)
                        ):
                            raise FingerprintError(
                                f"artifact directory changed during scan: {relative}"
                            )
                    finally:
                        os.close(child_fd)
                elif item.is_file(follow_symlinks=False):
                    if relative != manifest:
                        records.append(
                            _file_identity(
                                relative, Path(item.name), directory_fd=directory_fd
                            )
                        )
                else:
                    raise FingerprintError(
                        f"artifact contains non-regular entry: {relative}"
                    )
            except OSError as exc:
                raise FingerprintError(
                    f"cannot inspect artifact entry {relative}"
                ) from exc

    try:
        root_fd = os.open(root, flags)
    except OSError as exc:
        raise FingerprintError(f"cannot open artifact directory {root}") from exc
    try:
        first_root = os.fstat(root_fd)
        if not stat.S_ISDIR(first_root.st_mode):
            raise FingerprintError(f"artifact root is not a directory: {root}")
        walk(root_fd, "")
        last_root = os.fstat(root_fd)
        current_root = root.lstat()
        if (
            not stat.S_ISDIR(current_root.st_mode)
            or (first_root.st_dev, first_root.st_ino)
            != (last_root.st_dev, last_root.st_ino)
            or (current_root.st_dev, current_root.st_ino)
            != (last_root.st_dev, last_root.st_ino)
        ):
            raise FingerprintError(f"artifact root changed during scan: {root}")
    except OSError as exc:
        raise FingerprintError(f"cannot inspect artifact root {root}") from exc
    finally:
        os.close(root_fd)
    try:
        records.sort(key=lambda item: item.path.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise FingerprintError(
            "artifact contains a filename not representable as UTF-8"
        ) from exc
    return records


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

    records = (
        tuple(_anchored_files(directory, manifest))
        if os.name == "posix"
        else tuple(_file_identity(name, path) for name, path in _files(directory, manifest))
    )
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
