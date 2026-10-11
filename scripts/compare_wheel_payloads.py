"""Compare the installed tf_build package files of direct and sdist-rebuilt wheels.

ZIP timestamps and dist-info metadata can legitimately differ.  This tool does
not extract or execute any archive entries.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import stat
import zipfile
from pathlib import Path

_DIST_INFO = re.compile(r"tf_build-[^/]+\.dist-info\Z")
_CHUNK = 1024 * 1024


class WheelPayloadMismatch(ValueError):
    """A candidate wheel is unsafe or has a different installed package payload."""


def _package_payload(wheel: Path) -> dict[str, str]:
    """Read all installed tf_build files, rejecting ambiguous ZIP layouts."""
    if wheel.is_symlink() or not wheel.is_file():
        raise WheelPayloadMismatch(f"wheel is not a regular file: {wheel.name}")
    files: dict[str, str] = {}
    entries: set[str] = set()
    installed_paths: set[str] = set()
    file_paths: set[str] = set()
    directory_paths: set[str] = set()
    try:
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.infolist():
                name = member.filename
                parts = name.rstrip("/").split("/")
                if (
                    not name
                    or name.startswith("/")
                    or "\\" in name
                    or "\x00" in name
                    or name.endswith("//")
                    or any(part in {"", ".", ".."} for part in parts)
                    or (parts and ":" in parts[0])
                ):
                    raise WheelPayloadMismatch(f"unsafe wheel ZIP entry: {name!r}")
                kind = stat.S_IFMT(member.external_attr >> 16)
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise WheelPayloadMismatch(f"nonregular wheel ZIP entry: {name!r}")
                if member.is_dir() and kind not in (0, stat.S_IFDIR):
                    raise WheelPayloadMismatch(f"invalid directory entry: {name!r}")
                if not parts or not (
                    parts[0] == "tf_build" or _DIST_INFO.fullmatch(parts[0])
                ):
                    raise WheelPayloadMismatch(f"unexpected installed wheel path: {name!r}")
                if not member.is_dir() and kind == stat.S_IFDIR:
                    raise WheelPayloadMismatch(f"directory pretending to be a file: {name!r}")

                # ZIP names can be distinct yet map to the same installed path.
                # Track implicit parents as well as explicit directory records.
                normalized = name.rstrip("/")
                if name in entries:
                    raise WheelPayloadMismatch(f"duplicate wheel ZIP entry: {name!r}")
                entries.add(name)
                if normalized in installed_paths:
                    raise WheelPayloadMismatch(f"colliding wheel ZIP path: {name!r}")
                installed_paths.add(normalized)
                if any(
                    "/".join(parts[:depth]) in file_paths
                    for depth in range(1, len(parts))
                ):
                    raise WheelPayloadMismatch(f"file ancestor in wheel ZIP path: {name!r}")
                if not member.is_dir() and normalized in directory_paths:
                    raise WheelPayloadMismatch(f"file collides with wheel ZIP directory: {name!r}")
                if member.is_dir():
                    directory_paths.add(normalized)
                else:
                    file_paths.add(normalized)
                for depth in range(1, len(parts)):
                    directory_paths.add("/".join(parts[:depth]))
                if member.is_dir():
                    continue
                if parts[0] != "tf_build":
                    continue
                if len(parts) < 2:
                    raise WheelPayloadMismatch(f"invalid package file path: {name!r}")
                digest = hashlib.sha256()
                with archive.open(member) as stream:
                    while block := stream.read(_CHUNK):
                        digest.update(block)
                files[name] = digest.hexdigest()
    except (OSError, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise WheelPayloadMismatch(f"could not inspect wheel: {wheel.name}") from exc
    if "tf_build/__init__.py" not in files:
        raise WheelPayloadMismatch("wheel lacks tf_build/__init__.py package initializer")
    return files


def compare_wheel_payloads(direct: Path, rebuilt: Path) -> tuple[str, ...]:
    """Require identical unpacked package paths and bytes in two wheels."""
    source = _package_payload(direct)
    candidate = _package_payload(rebuilt)
    missing = sorted(source.keys() - candidate.keys())
    added = sorted(candidate.keys() - source.keys())
    changed = sorted(
        name for name in source.keys() & candidate.keys()
        if source[name] != candidate[name]
    )
    if missing or added or changed:
        details = []
        if missing:
            details.append(f"missing from rebuilt: {', '.join(missing)}")
        if added:
            details.append(f"unexpected in rebuilt: {', '.join(added)}")
        if changed:
            details.append(f"changed package bytes: {', '.join(changed)}")
        raise WheelPayloadMismatch("; ".join(details))
    return tuple(sorted(source))


def _one_wheel(directory: Path) -> Path:
    wheels = sorted(directory.glob("*.whl"))
    if len(wheels) != 1:
        raise WheelPayloadMismatch(
            f"expected exactly one wheel in {directory}, found {len(wheels)}"
        )
    return wheels[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direct-dir", type=Path, required=True)
    parser.add_argument("--rebuilt-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    files = compare_wheel_payloads(
        _one_wheel(args.direct_dir), _one_wheel(args.rebuilt_dir)
    )
    print(f"Verified matching direct/sdist wheel payload: {len(files)} package files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
