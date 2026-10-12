"""Validate a built tf-build wheel and record exact wheel/source identities.

This is CI development-artifact evidence, not a signed release attestation.

Example:
    python scripts/wheel_manifest.py --wheel-dir WHEELS --pyproject pyproject.toml \
        --revision FULL_GIT_SHA --wheelhouse WHEELHOUSE --output WHEELS/manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tarfile
import tempfile
import tomllib
import zipfile
from collections.abc import Callable
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

_REVISION = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")


class WheelManifestError(ValueError):
    """A wheel cannot be unambiguously bound to this project and source."""


def _identity(
    wheel: Path, *, inspector: Callable[[BinaryIO], None] | None = None
) -> dict[str, str | int]:
    """Hash a stable regular file, never following raced symlinks on POSIX."""
    if wheel.is_symlink() or not wheel.is_file():
        raise WheelManifestError(f"wheel is not a regular file: {wheel.name}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if os.name == "posix":
        nofollow = getattr(os, "O_NOFOLLOW", None)
        nonblocking = getattr(os, "O_NONBLOCK", None)
        if nofollow is None or nonblocking is None:
            raise WheelManifestError("safe POSIX manifest file open flags unavailable")
        flags |= nofollow | nonblocking

    try:
        initial = wheel.lstat()
        if not stat.S_ISREG(initial.st_mode):
            raise WheelManifestError(f"wheel is not a regular file: {wheel.name}")
        fd = os.open(wheel, flags)
        with os.fdopen(fd, "rb") as stream:
            first = os.fstat(stream.fileno())
            if not stat.S_ISREG(first.st_mode) or (
                initial.st_dev,
                initial.st_ino,
            ) != (first.st_dev, first.st_ino):
                raise WheelManifestError(f"wheel identity changed during open: {wheel.name}")
            # Keep inspection and digest on this one verified regular FD.
            # zipfile/tarfile may seek within the stream; rewind before SHA256.
            if inspector is not None:
                inspector(stream)
                stream.seek(0)
            digest = hashlib.sha256()
            size = 0
            while block := stream.read(1024 * 1024):
                digest.update(block)
                size += len(block)
            last = os.fstat(stream.fileno())
        current = wheel.lstat()
    except OSError as exc:
        raise WheelManifestError(f"wheel cannot be safely hashed: {wheel.name}") from exc

    opened_identity = (
        first.st_dev, first.st_ino, first.st_size,
        first.st_mtime_ns, first.st_ctime_ns,
    )
    completed_identity = (
        last.st_dev, last.st_ino, last.st_size,
        last.st_mtime_ns, last.st_ctime_ns,
    )
    if (
        opened_identity != completed_identity
        or size != last.st_size
        or not stat.S_ISREG(current.st_mode)
        or (
            current.st_dev, current.st_ino, current.st_size,
            current.st_mtime_ns, current.st_ctime_ns,
        )
        != (
            last.st_dev, last.st_ino, last.st_size,
            last.st_mtime_ns, last.st_ctime_ns,
        )
    ):
        raise WheelManifestError(f"wheel changed during hashing: {wheel.name}")
    return {"file": wheel.name, "bytes": size, "sha256": digest.hexdigest()}


_RELEASE_VERSION = re.compile(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?\Z")
_MAX_METADATA_BYTES = 1024 * 1024


def _check_package_identity(payload: bytes, name: str, version: str, source: str) -> None:
    """Reject malformed or ambiguous required Core Metadata identity headers."""
    metadata = BytesParser().parsebytes(payload)
    if metadata.defects:
        raise WheelManifestError(f"{source} metadata has malformed headers")
    for field in ("Metadata-Version", "Name", "Version"):
        values = metadata.get_all(field) or ()
        if len(values) != 1 or not str(values[0]).strip():
            raise WheelManifestError(f"{source} metadata requires exactly one {field}")
        if field == "Name" and str(values[0]).strip() != name:
            raise WheelManifestError(f"{source} metadata Name disagrees with project")
        if field == "Version" and str(values[0]).strip() != version:
            raise WheelManifestError(f"{source} metadata Version disagrees with project")


def _sdist_identity(sdist_dir: Path, name: str, version: str) -> dict[str, str | int]:
    sdists = sorted(sdist_dir.glob("*.tar.gz"))
    if len(sdists) != 1:
        raise WheelManifestError("expected exactly one source distribution sdist")
    path = sdists[0]
    root = f"tf_build-{version}"
    if path.name != f"{root}.tar.gz":
        raise WheelManifestError("sdist filename does not match project version")
    expected_meta = f"{root}/PKG-INFO"

    def inspect(stream: BinaryIO) -> None:
        found_meta = False
        entries: set[str] = set()
        regular_files: set[str] = set()
        directories: set[str] = set()
        with tarfile.open(fileobj=stream, mode="r:gz") as archive:
            for member in archive:
                filename = member.name
                parts = PurePosixPath(filename).parts
                if (
                    not parts
                    or parts[0] != root
                    or filename.startswith("/")
                    or "\\" in filename
                    or any(part in {"", ".", ".."} for part in filename.split("/"))
                    or filename in entries
                    or not (member.isfile() or member.isdir())
                ):
                    raise WheelManifestError("sdist contains unsafe or ambiguous archive entry")
                entries.add(filename)
                # Reject a regular-file ancestor in either member order.
                # Explicit declarations of previously implied dirs are fine.
                parents = {"/".join(parts[:depth]) for depth in range(1, len(parts))}
                if parents & regular_files:
                    raise WheelManifestError("sdist has a regular-file ancestor")
                if member.isfile() and filename in directories:
                    raise WheelManifestError("sdist file collides with a directory")
                directories.update(parents)
                if member.isdir():
                    directories.add(filename)
                else:
                    regular_files.add(filename)
                if filename == expected_meta:
                    if not member.isfile() or member.size > _MAX_METADATA_BYTES:
                        raise WheelManifestError("sdist metadata is invalid")
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise WheelManifestError("sdist metadata cannot be read")
                    with extracted:
                        payload = extracted.read(_MAX_METADATA_BYTES + 1)
                    if len(payload) > _MAX_METADATA_BYTES:
                        raise WheelManifestError("sdist metadata exceeds limit")
                    _check_package_identity(payload, name, version, "sdist")
                    found_meta = True
        if not found_meta:
            raise WheelManifestError("sdist root PKG-INFO metadata is missing")

    try:
        return _identity(path, inspector=inspect)
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise WheelManifestError("sdist source distribution cannot be inspected") from exc

def build_wheel_manifest(
    wheel_dir: Path,
    pyproject: Path,
    revision: str,
    *,
    wheelhouse: Path | None = None,
    sdist_dir: Path | None = None,
    release_tag: str | None = None,
) -> dict[str, Any]:
    """Inspect the actual wheel ZIP without importing or executing its contents."""
    if not isinstance(revision, str) or _REVISION.fullmatch(revision) is None:
        raise WheelManifestError("source commit must be a full immutable Git SHA")
    try:
        with pyproject.open("rb") as stream:
            project = tomllib.load(stream)["project"]
        name = project["name"]
        version = project["version"]
    except (OSError, KeyError, ValueError, TypeError) as exc:
        raise WheelManifestError("could not read project name/version") from exc
    if name != "tf-build" or not isinstance(version, str) or not version:
        raise WheelManifestError("unsupported project wheel name or version")

    if release_tag is not None:
        if sdist_dir is None:
            raise WheelManifestError("release tag requires an sdist")
        if _RELEASE_VERSION.fullmatch(version) is None or release_tag != f"v{version}":
            raise WheelManifestError("release tag must match a versioned project release")

    wheels = sorted(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise WheelManifestError("expected exactly one project wheel")
    wheel = wheels[0]
    expected_prefix = f"tf_build-{version}-"
    metadata_path = f"tf_build-{version}.dist-info/METADATA"
    if not wheel.name.startswith(expected_prefix):
        raise WheelManifestError("wheel filename does not match project name/version")

    def inspect(stream: BinaryIO) -> None:
        with zipfile.ZipFile(stream) as archive:
            meta_paths = [
                item.filename
                for item in archive.infolist()
                if item.filename.endswith(".dist-info/METADATA")
            ]
            if meta_paths != [metadata_path]:
                raise WheelManifestError("wheel embedded metadata path is ambiguous")
            member = archive.getinfo(metadata_path)
            if member.file_size > _MAX_METADATA_BYTES:
                raise WheelManifestError("wheel metadata exceeds size limit")
            with archive.open(member) as metadata_stream:
                metadata_bytes = metadata_stream.read(_MAX_METADATA_BYTES + 1)
            if len(metadata_bytes) > _MAX_METADATA_BYTES:
                raise WheelManifestError("wheel metadata exceeds size limit")
            _check_package_identity(metadata_bytes, name, version, "wheel")

    try:
        wheel_identity = _identity(wheel, inspector=inspect)
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        raise WheelManifestError("wheel ZIP/metadata cannot be inspected") from exc

    record: dict[str, Any] = {
        "schema": 1,
        "package": name,
        "version": version,
        "source_commit": revision.lower(),
        "wheel": wheel_identity,
    }
    if sdist_dir is not None:
        record["sdist"] = _sdist_identity(sdist_dir, name, version)
    if release_tag is not None:
        record["release_tag"] = release_tag
    if wheelhouse is not None:
        dependencies = sorted(wheelhouse.glob("*.whl"))
        if not dependencies:
            raise WheelManifestError("wheelhouse has no wheels")
        records = [_identity(path) for path in dependencies]
        if not any(
            item["file"] == wheel.name and item["sha256"] == record["wheel"]["sha256"]
            for item in records
        ):
            raise WheelManifestError("wheelhouse lacks the identical project wheel")
        record["wheelhouse"] = records
    return record


def write_wheel_manifest(path: Path, record: dict[str, Any]) -> None:
    """Publish a complete canonical manifest without replacing existing evidence."""
    # Serialize before creating files so invalid records leave no output.
    payload = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode("utf-8")
    staging: Path | None = None
    try:
        # A sibling temporary file permits an atomic, create-only hardlink.
        # Never expose incomplete evidence at the final destination pathname.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            staging = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Unlike os.replace, hardlink creation refuses an existing pathname.
        os.link(staging, path)
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--pyproject", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--sdist-dir", type=Path)
    parser.add_argument("--release-tag")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_wheel_manifest(
        args.wheel_dir,
        args.pyproject,
        args.revision,
        wheelhouse=args.wheelhouse,
        sdist_dir=args.sdist_dir,
        release_tag=args.release_tag,
    )
    write_wheel_manifest(args.output, manifest)


if __name__ == "__main__":
    main()
