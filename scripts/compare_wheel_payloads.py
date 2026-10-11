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
from email.parser import BytesParser
from pathlib import Path

_DIST_INFO = re.compile(r"tf_build-[^/]+\.dist-info\Z")
_CHUNK = 1024 * 1024
_MAX_RUNTIME_METADATA = 1024 * 1024
_MAX_ENTRY_POINTS = 64 * 1024
_MAX_WHEEL_METADATA = 64 * 1024
_RUNTIME_FIELDS = ("Name", "Version", "Requires-Python", "Requires-Dist", "Provides-Extra")
_WHEEL_VERSION = re.compile(r"1\.[0-9]+\Z")
_WHEEL_TAG = re.compile(r"[A-Za-z0-9_.]+-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+\Z")


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


def _read_bounded(archive: zipfile.ZipFile, name: str, limit: int) -> bytes:
    """Read a small wheel metadata file without extraction or unbounded allocation."""
    member = archive.getinfo(name)
    if member.file_size > limit:
        raise WheelPayloadMismatch(f"wheel runtime metadata is too large: {name!r}")
    with archive.open(member) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise WheelPayloadMismatch(f"wheel runtime metadata exceeds limit: {name!r}")
    return data



def _wheel_install_contract(raw: bytes) -> tuple[str, str, tuple[str, ...], str | None]:
    """Read WHEEL install compatibility without executing candidate distribution code."""
    metadata = BytesParser().parsebytes(raw)
    if metadata.defects:
        raise WheelPayloadMismatch("WHEEL has malformed metadata headers")

    def exactly_one(field: str) -> str:
        values = metadata.get_all(field) or ()
        if len(values) != 1 or not str(values[0]).strip():
            raise WheelPayloadMismatch(f"WHEEL requires exactly one nonempty {field}")
        return str(values[0]).strip()

    version = exactly_one("Wheel-Version")
    if _WHEEL_VERSION.fullmatch(version) is None:
        raise WheelPayloadMismatch("WHEEL has unsupported Wheel-Version major or syntax")

    purelib = exactly_one("Root-Is-Purelib")
    if purelib not in {"true", "false"}:
        raise WheelPayloadMismatch("WHEEL has invalid Root-Is-Purelib value")

    raw_tags = metadata.get_all("Tag") or ()
    tags = tuple(sorted(str(tag).strip() for tag in raw_tags))
    if not tags or any(_WHEEL_TAG.fullmatch(tag) is None for tag in tags):
        raise WheelPayloadMismatch("WHEEL requires valid nonempty compatibility Tag")

    builds = metadata.get_all("Build") or ()
    if len(builds) > 1 or (builds and not str(builds[0]).strip()):
        raise WheelPayloadMismatch("WHEEL has ambiguous Build value")
    build = str(builds[0]).strip() if builds else None
    return version, purelib, tags, build


def _runtime_contract(
    wheel: Path,
) -> tuple[tuple[tuple[str, tuple[str, ...]], ...], bytes | None, tuple[str, str, tuple[str, ...], str | None]]:
    """Compare install-relevant metadata while permitting generated metadata drift."""
    try:
        with zipfile.ZipFile(wheel) as archive:
            roots: set[str] = set()
            names = set(archive.namelist())
            for name in names:
                root = name.split("/", 1)[0]
                if _DIST_INFO.fullmatch(root):
                    roots.add(root)
            if len(roots) != 1:
                raise WheelPayloadMismatch("wheel has ambiguous runtime metadata roots")
            root = next(iter(roots))
            metadata_path = f"{root}/METADATA"
            if metadata_path not in names:
                raise WheelPayloadMismatch("wheel lacks runtime METADATA")
            raw = _read_bounded(archive, metadata_path, _MAX_RUNTIME_METADATA)
            wheel_path = f"{root}/WHEEL"
            if wheel_path not in names:
                raise WheelPayloadMismatch("wheel lacks required WHEEL installation metadata")
            wheel_headers = _read_bounded(archive, wheel_path, _MAX_WHEEL_METADATA)
            entry_path = f"{root}/entry_points.txt"
            entry_points = (
                _read_bounded(archive, entry_path, _MAX_ENTRY_POINTS)
                if entry_path in names
                else None
            )
    except (OSError, zipfile.BadZipFile, RuntimeError, EOFError, KeyError) as exc:
        raise WheelPayloadMismatch(
            f"could not inspect wheel runtime metadata: {wheel.name}"
        ) from exc

    metadata = BytesParser().parsebytes(raw)
    if metadata.defects:
        raise WheelPayloadMismatch("wheel runtime metadata has malformed headers")
    for key in ("Metadata-Version", "Name", "Version"):
        values = metadata.get_all(key) or ()
        if len(values) != 1 or not str(values[0]).strip():
            raise WheelPayloadMismatch(f"wheel runtime metadata requires one {key}")
    fields: list[tuple[str, tuple[str, ...]]] = []
    for key in _RUNTIME_FIELDS:
        values = metadata.get_all(key) or ()
        normalized = tuple(sorted(str(value).strip() for value in values))
        if any(not value for value in normalized):
            raise WheelPayloadMismatch(f"wheel runtime metadata has empty {key}")
        fields.append((key, normalized))
    return tuple(fields), entry_points, _wheel_install_contract(wheel_headers)


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
    if _runtime_contract(direct) != _runtime_contract(rebuilt):
        raise WheelPayloadMismatch("wheel runtime metadata/entry point contract differs")
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
