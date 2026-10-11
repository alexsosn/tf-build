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
import re
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Any

_REVISION = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")


class WheelManifestError(ValueError):
    """A wheel cannot be unambiguously bound to this project and source."""


def _identity(wheel: Path) -> dict[str, str | int]:
    if wheel.is_symlink() or not wheel.is_file():
        raise WheelManifestError(f"wheel is not a regular file: {wheel.name}")
    digest = hashlib.sha256()
    with wheel.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return {"file": wheel.name, "bytes": wheel.stat().st_size, "sha256": digest.hexdigest()}


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
    found_meta = False
    entries: set[str] = set()
    try:
        with tarfile.open(path, mode="r:gz") as archive:
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
                if filename == expected_meta:
                    if not member.isfile() or member.size > _MAX_METADATA_BYTES:
                        raise WheelManifestError("sdist metadata is invalid")
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise WheelManifestError("sdist metadata cannot be read")
                    with stream:
                        payload = stream.read(_MAX_METADATA_BYTES + 1)
                    if len(payload) > _MAX_METADATA_BYTES:
                        raise WheelManifestError("sdist metadata exceeds limit")
                    _check_package_identity(payload, name, version, "sdist")
                    found_meta = True
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise WheelManifestError("sdist source distribution cannot be inspected") from exc
    if not found_meta:
        raise WheelManifestError("sdist root PKG-INFO metadata is missing")
    return _identity(path)


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

    try:
        with zipfile.ZipFile(wheel) as archive:
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
            with archive.open(member) as stream:
                metadata_bytes = stream.read(_MAX_METADATA_BYTES + 1)
            if len(metadata_bytes) > _MAX_METADATA_BYTES:
                raise WheelManifestError("wheel metadata exceeds size limit")
            _check_package_identity(metadata_bytes, name, version, "wheel")
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        raise WheelManifestError("wheel ZIP/metadata cannot be inspected") from exc

    record: dict[str, Any] = {
        "schema": 1,
        "package": name,
        "version": version,
        "source_commit": revision.lower(),
        "wheel": _identity(wheel),
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
    """Write canonical JSON exclusively; never overwrite previous evidence."""
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, indent=2) + "\n")


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
