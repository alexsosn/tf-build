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
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path
from typing import Any

_REVISION = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\\Z")


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


def build_wheel_manifest(
    wheel_dir: Path,
    pyproject: Path,
    revision: str,
    *,
    wheelhouse: Path | None = None,
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
            metadata = BytesParser().parsebytes(archive.read(metadata_path))
            if metadata.get("Name") != name or metadata.get("Version") != version:
                raise WheelManifestError("wheel metadata disagrees with pyproject")
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        raise WheelManifestError("wheel ZIP/metadata cannot be inspected") from exc

    record: dict[str, Any] = {
        "schema": 1,
        "package": name,
        "version": version,
        "source_commit": revision.lower(),
        "wheel": _identity(wheel),
    }
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_wheel_manifest(
        args.wheel_dir, args.pyproject, args.revision, wheelhouse=args.wheelhouse
    )
    write_wheel_manifest(args.output, manifest)


if __name__ == "__main__":
    main()
