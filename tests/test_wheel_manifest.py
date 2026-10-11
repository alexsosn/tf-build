"""RED-first tests of wheel-byte identity and embedded package metadata."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts.wheel_manifest import (
    WheelManifestError,
    build_wheel_manifest,
    write_wheel_manifest,
)


def _fixture(tmp_path: Path, *, version: str = "0.1.0.dev0") -> tuple[Path, Path, Path]:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "tf-build"\nversion = "0.1.0.dev0"\n',
        encoding="utf-8",
    )
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    wheel = wheels / f"tf_build-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"tf_build-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.3\nName: tf-build\nVersion: {version}\n",
        )
    return pyproject, wheels, wheel


def test_manifest_is_bound_to_exact_wheel_bytes_and_source_sha(tmp_path: Path) -> None:
    project, wheels, wheel = _fixture(tmp_path)
    info = build_wheel_manifest(wheels, project, "A" * 40)
    assert info["source_commit"] == "a" * 40
    assert info["package"] == "tf-build"
    assert info["version"] == "0.1.0.dev0"
    assert info["wheel"]["file"] == wheel.name
    assert info["wheel"]["sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert info["wheel"]["bytes"] == wheel.stat().st_size
    assert info == build_wheel_manifest(wheels, project, "a" * 40)

    out = tmp_path / "wheel-manifest.json"
    write_wheel_manifest(out, info)
    payload = out.read_text(encoding="utf-8")
    assert payload == json.dumps(info, sort_keys=True, indent=2) + "\n"
    with pytest.raises(FileExistsError):
        write_wheel_manifest(out, info)
    assert out.read_text(encoding="utf-8") == payload


def test_manifest_includes_hash_inventory_of_prepared_offline_wheelhouse(
    tmp_path: Path,
) -> None:
    project, wheels, wheel = _fixture(tmp_path)
    warehouse = tmp_path / "wheelhouse"
    warehouse.mkdir()
    (warehouse / wheel.name).write_bytes(wheel.read_bytes())
    dep = warehouse / "example-1.0-py3-none-any.whl"
    dep.write_bytes(b"test byte identity only")
    info = build_wheel_manifest(wheels, project, "b" * 64, wheelhouse=warehouse)
    assert info["source_commit"] == "b" * 64
    identities = info["wheelhouse"]
    assert [item["file"] for item in identities] == sorted([wheel.name, dep.name])
    assert any(
        item["file"] == dep.name
        and item["sha256"] == hashlib.sha256(dep.read_bytes()).hexdigest()
        for item in identities
    )


@pytest.mark.parametrize("revision", ["main", "a" * 39, "f" * 65, "z" * 40, ""])
def test_invalid_source_revision_fails_before_manifest_written(
    tmp_path: Path, revision: str
) -> None:
    project, wheels, _ = _fixture(tmp_path)
    with pytest.raises(WheelManifestError, match="commit"):
        build_wheel_manifest(wheels, project, revision)
    assert not (tmp_path / "wheel-manifest.json").exists()


def test_multiple_and_missing_wheels_fail_closed(tmp_path: Path) -> None:
    project, wheels, wheel = _fixture(tmp_path)
    second = wheels / "tf_build-0.1.0.dev0-py2-none-any.whl"
    second.write_bytes(wheel.read_bytes())
    with pytest.raises(WheelManifestError, match="exactly one"):
        build_wheel_manifest(wheels, project, "a" * 40)
    second.unlink()
    wheel.unlink()
    with pytest.raises(WheelManifestError, match="exactly one"):
        build_wheel_manifest(wheels, project, "a" * 40)


@pytest.mark.parametrize("mismatch", ["wrong-wheel-name", "wrong-version", "corrupt-zip"])
def test_mismatched_or_unreadable_wheel_is_rejected(
    tmp_path: Path, mismatch: str
) -> None:
    project, wheels, wheel = _fixture(tmp_path)
    if mismatch == "wrong-wheel-name":
        wheel.rename(wheels / "different-0.1.0.dev0-py3-none-any.whl")
    elif mismatch == "wrong-version":
        wheel.unlink()
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(
                "tf_build-0.1.0.dev0.dist-info/METADATA",
                "Metadata-Version: 2.3\nName: tf-build\nVersion: 1.0.0\n",
            )
    else:
        wheel.write_bytes(b"not a valid ZIP wheel")
    with pytest.raises(WheelManifestError):
        build_wheel_manifest(wheels, project, "a" * 40)


def test_wheelhouse_must_include_same_project_wheel(tmp_path: Path) -> None:
    project, wheels, _ = _fixture(tmp_path)
    warehouse = tmp_path / "wheelhouse"
    warehouse.mkdir()
    with pytest.raises(WheelManifestError, match="wheelhouse"):
        build_wheel_manifest(wheels, project, "a" * 40, wheelhouse=warehouse)
