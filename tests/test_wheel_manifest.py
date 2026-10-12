"""RED-first tests of wheel-byte identity and embedded package metadata."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

import scripts.wheel_manifest as manifest_module
from scripts.wheel_manifest import (
    WheelManifestError,
    build_wheel_manifest,
    write_wheel_manifest,
)


def _fixture(tmp_path: Path, *, version: str = "0.1.0.dev0") -> tuple[Path, Path, Path]:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        f'[project]\nname = "tf-build"\nversion = "{version}"\n',
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


def _sdist_fixture(
    tmp_path: Path,
    *,
    version: str = "0.1.0rc1",
    metadata_version: str | None = None,
    extra_name: str | None = None,
    extra_kind: str = "file",
) -> tuple[Path, Path, Path]:
    project, wheels, _ = _fixture(tmp_path, version=version)
    sdist_dir = tmp_path / "sdist"
    sdist_dir.mkdir()
    package_root = f"tf_build-{version}"
    archive = sdist_dir / f"{package_root}.tar.gz"
    metadata = (
        "Metadata-Version: 2.3\nName: tf-build\n"
        f"Version: {version if metadata_version is None else metadata_version}\n"
    ).encode()
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(f"{package_root}/PKG-INFO")
        info.size = len(metadata)
        tar.addfile(info, io.BytesIO(metadata))
        if extra_name is not None:
            item = tarfile.TarInfo(extra_name)
            if extra_kind == "symlink":
                item.type = tarfile.SYMTYPE
                item.linkname = "../escape"
                tar.addfile(item)
            else:
                body = b"test data"
                item.size = len(body)
                tar.addfile(item, io.BytesIO(body))
    return project, wheels, archive


def test_release_candidate_version_is_distinct_from_mutable_development_build() -> None:
    with (Path(__file__).parents[1] / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    assert project["version"] == "0.1.0rc1"


def test_release_manifest_binds_both_wheel_and_sdist_and_full_git_sha(
    tmp_path: Path,
) -> None:
    project, wheels, sdist = _sdist_fixture(tmp_path)
    record = build_wheel_manifest(
        wheels,
        project,
        "f" * 40,
        sdist_dir=sdist.parent,
        release_tag="v0.1.0rc1",
    )
    assert record["source_commit"] == "f" * 40
    assert record["version"] == "0.1.0rc1"
    assert record["release_tag"] == "v0.1.0rc1"
    assert record["sdist"]["file"] == sdist.name
    assert record["sdist"]["sha256"] == hashlib.sha256(sdist.read_bytes()).hexdigest()
    assert record == build_wheel_manifest(
        wheels, project, "f" * 40, sdist_dir=sdist.parent, release_tag="v0.1.0rc1"
    )


@pytest.mark.parametrize("tag", ["v0.1.0", "v0.1.0rc2", "main", "0.1.0rc1", ""])
def test_release_manifest_rejects_nonmatching_or_ambiguous_tag(
    tmp_path: Path, tag: str
) -> None:
    project, wheels, sdist = _sdist_fixture(tmp_path)
    with pytest.raises(WheelManifestError, match="tag"):
        build_wheel_manifest(
            wheels, project, "a" * 40, sdist_dir=sdist.parent, release_tag=tag
        )


@pytest.mark.parametrize("failure", ["missing", "multiple", "wrong-metadata", "bad-tar"])
def test_release_manifest_rejects_nonunique_or_corrupt_source_distribution(
    tmp_path: Path, failure: str
) -> None:
    project, wheels, sdist = _sdist_fixture(
        tmp_path, metadata_version="0.1.0" if failure == "wrong-metadata" else None
    )
    if failure == "missing":
        sdist.unlink()
    elif failure == "multiple":
        (sdist.parent / "tf_build-0.1.0rc1-copy.tar.gz").write_bytes(sdist.read_bytes())
    elif failure == "bad-tar":
        sdist.write_bytes(b"bad gzip")
    with pytest.raises(WheelManifestError, match="sdist|source distribution"):
        build_wheel_manifest(
            wheels, project, "a" * 40, sdist_dir=sdist.parent, release_tag="v0.1.0rc1"
        )


@pytest.mark.parametrize(
    ("extra_name", "extra_kind"),
    [
        ("tf_build-0.1.0rc1/../../escape", "file"),
        ("/absolute", "file"),
        ("tf_build-0.1.0rc1/link", "symlink"),
    ],
)
def test_release_manifest_rejects_malicious_archive_entries(
    tmp_path: Path, extra_name: str, extra_kind: str
) -> None:
    project, wheels, sdist = _sdist_fixture(
        tmp_path, extra_name=extra_name, extra_kind=extra_kind
    )
    with pytest.raises(WheelManifestError, match="sdist|source distribution"):
        build_wheel_manifest(
            wheels, project, "a" * 40, sdist_dir=sdist.parent, release_tag="v0.1.0rc1"
        )


def test_release_manifest_requires_sdist_when_a_release_tag_is_given(
    tmp_path: Path,
) -> None:
    project, wheels, _ = _fixture(tmp_path, version="0.1.0rc1")
    with pytest.raises(WheelManifestError, match="sdist"):
        build_wheel_manifest(wheels, project, "a" * 40, release_tag="v0.1.0rc1")


_VALID_WHEEL_META = (
    b"Metadata-Version: 2.3\n"
    b"Name: tf-build\n"
    b"Version: 0.1.0.dev0\n"
)
_VALID_SDIST_META = _VALID_WHEEL_META.replace(b"0.1.0.dev0", b"0.1.0rc1")


@pytest.mark.parametrize(
    "invalid",
    [
        _VALID_WHEEL_META + b"Name: different-project\n",
        _VALID_WHEEL_META + b"Version: 9.9.9\n",
        _VALID_WHEEL_META + b"Metadata-Version: 2.4\n",
        _VALID_WHEEL_META.replace(b"Metadata-Version: 2.3\n", b""),
        _VALID_WHEEL_META.replace(b"Name: tf-build\n", b""),
        _VALID_WHEEL_META.replace(b"Version: 0.1.0.dev0\n", b""),
        _VALID_WHEEL_META + b"Broken-Header-Without-Colon\n",
    ],
)
def test_wheel_manifest_rejects_ambiguous_required_metadata(
    tmp_path: Path, invalid: bytes
) -> None:
    project, wheels, wheel = _fixture(tmp_path)
    with zipfile.ZipFile(wheel, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("tf_build-0.1.0.dev0.dist-info/METADATA", invalid)
    with pytest.raises(WheelManifestError, match="metadata|identity|ambiguous"):
        build_wheel_manifest(wheels, project, "a" * 40)


def test_manifest_bounds_compressed_wheel_metadata(tmp_path: Path) -> None:
    project, wheels, wheel = _fixture(tmp_path)
    huge = _VALID_WHEEL_META + b"Summary: " + b"x" * (1024 * 1024 + 1)
    with zipfile.ZipFile(wheel, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("tf_build-0.1.0.dev0.dist-info/METADATA", huge)
    assert wheel.stat().st_size < 10_000  # compressed bomb-like metadata
    with pytest.raises(WheelManifestError, match="metadata|size|large|limit"):
        build_wheel_manifest(wheels, project, "a" * 40)


@pytest.mark.parametrize(
    "invalid",
    [
        _VALID_SDIST_META + b"Name: different-project\n",
        _VALID_SDIST_META + b"Version: 9.9.9\n",
        _VALID_SDIST_META + b"Metadata-Version: 2.4\n",
        _VALID_SDIST_META.replace(b"Metadata-Version: 2.3\n", b""),
        _VALID_SDIST_META.replace(b"Name: tf-build\n", b""),
        _VALID_SDIST_META.replace(b"Version: 0.1.0rc1\n", b""),
        _VALID_SDIST_META + b"Broken-Header-Without-Colon\n",
    ],
)
def test_sdist_manifest_rejects_ambiguous_required_metadata(
    tmp_path: Path, invalid: bytes
) -> None:
    project, wheels, sdist = _sdist_fixture(tmp_path)
    with tarfile.open(sdist, mode="w:gz") as tar:
        member = tarfile.TarInfo("tf_build-0.1.0rc1/PKG-INFO")
        member.size = len(invalid)
        tar.addfile(member, io.BytesIO(invalid))
    with pytest.raises(WheelManifestError, match="metadata|identity|ambiguous"):
        build_wheel_manifest(
            wheels, project, "a" * 40, sdist_dir=sdist.parent,
            release_tag="v0.1.0rc1",
        )


def _tar_members(path: Path, entries: list[tuple[str, bytes | None]]) -> None:
    """Create a real source archive: None marks an explicit directory."""
    with tarfile.open(path, "w:gz") as tar:
        for name, payload in entries:
            member = tarfile.TarInfo(name)
            if payload is None:
                member.type = tarfile.DIRTYPE
                tar.addfile(member)
            else:
                member.size = len(payload)
                tar.addfile(member, io.BytesIO(payload))


@pytest.mark.parametrize("file_first", [False, True])
@pytest.mark.parametrize("file_as_ancestor", ["pkg", "root"])
def test_sdist_manifest_rejects_regular_file_ancestor_in_either_order(
    tmp_path: Path, file_first: bool, file_as_ancestor: str
) -> None:
    project, wheels, sdist = _sdist_fixture(tmp_path)
    root = "tf_build-0.1.0rc1"
    pkg_info = (f"{root}/PKG-INFO", _VALID_SDIST_META)
    members: list[tuple[str, bytes | None]]
    if file_as_ancestor == "pkg":
        ancestor = (f"{root}/pkg", b"regular file blocks this directory")
        descendant = (f"{root}/pkg/mod.py", b"MODULE = 1\n")
        members = [pkg_info, ancestor, descendant] if file_first else [
            pkg_info, descendant, ancestor,
        ]
    else:
        ancestor = (root, b"regular file blocks source root")
        members = [ancestor, pkg_info] if file_first else [pkg_info, ancestor]
    _tar_members(sdist, members)

    with pytest.raises(WheelManifestError, match="sdist|archive|ancestor|directory"):
        build_wheel_manifest(
            wheels, project, "a" * 40,
            sdist_dir=sdist.parent, release_tag="v0.1.0rc1",
        )


def test_sdist_manifest_accepts_explicit_and_implicit_parent_directories(
    tmp_path: Path,
) -> None:
    project, wheels, sdist = _sdist_fixture(tmp_path)
    root = "tf_build-0.1.0rc1"
    _tar_members(
        sdist,
        [
            (f"{root}/PKG-INFO", _VALID_SDIST_META),
            (f"{root}/pkg/mod.py", b"MODULE = 1\n"),
            (f"{root}/", None),
            (f"{root}/pkg/", None),
        ],
    )
    record = build_wheel_manifest(
        wheels, project, "a" * 40,
        sdist_dir=sdist.parent, release_tag="v0.1.0rc1",
    )
    assert record["sdist"]["sha256"] == hashlib.sha256(sdist.read_bytes()).hexdigest()


def test_sdist_manifest_preserves_explicit_file_directory_alias_rejection(
    tmp_path: Path,
) -> None:
    project, wheels, sdist = _sdist_fixture(tmp_path)
    root = "tf_build-0.1.0rc1"
    _tar_members(
        sdist,
        [
            (f"{root}/PKG-INFO", _VALID_SDIST_META),
            (f"{root}/pkg", b"file"),
            (f"{root}/pkg/", None),
        ],
    )
    with pytest.raises(WheelManifestError, match="sdist|ambiguous"):
        build_wheel_manifest(
            wheels, project, "a" * 40,
            sdist_dir=sdist.parent, release_tag="v0.1.0rc1",
        )


@pytest.mark.skipif(
    not hasattr(__import__("os"), "O_NOFOLLOW"),
    reason="POSIX nofollow semantics are required for symlink race test",
)
def test_manifest_identity_rejects_symlink_swap_after_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate.whl"
    candidate.write_bytes(b"approved-release-wheel")
    outside = tmp_path / "outside"
    outside.write_bytes(b"other-data-must-not-be-hashed")
    moved = tmp_path / "original"
    original_is_file = Path.is_file
    swapped = False

    def replace_when_checked(path: Path) -> bool:
        nonlocal swapped
        regular = original_is_file(path)
        if path == candidate and regular and not swapped:
            candidate.rename(moved)
            candidate.symlink_to(outside)
            swapped = True
        return regular

    monkeypatch.setattr(Path, "is_file", replace_when_checked)
    with pytest.raises(WheelManifestError, match="regular|changed|open|identity"):
        manifest_module._identity(candidate)
    assert swapped
    assert candidate.is_symlink()
    assert moved.read_bytes() == b"approved-release-wheel"


def test_manifest_identity_rejects_same_size_inode_swap_during_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate.whl"
    before = b"A" * 4096
    after = b"B" * len(before)
    candidate.write_bytes(before)
    moved = tmp_path / "original"
    native_sha256 = hashlib.sha256
    swapped = False

    class SwapAfterDigestUpdate:
        def __init__(self) -> None:
            self._digest = native_sha256()

        def update(self, chunk: bytes) -> None:
            nonlocal swapped
            self._digest.update(chunk)
            if not swapped:
                candidate.rename(moved)
                candidate.write_bytes(after)
                swapped = True

        def hexdigest(self) -> str:
            return self._digest.hexdigest()

    monkeypatch.setattr(hashlib, "sha256", SwapAfterDigestUpdate)
    with pytest.raises(WheelManifestError, match="changed|identity|stable|regular"):
        manifest_module._identity(candidate)
    assert swapped
    assert moved.read_bytes() == before
    assert candidate.read_bytes() == after


@pytest.mark.skipif(os.name != "posix", reason="atomic replace of open archive requires POSIX")
def test_wheel_manifest_rejects_replacement_after_embedded_metadata_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, wheels, wheel = _fixture(tmp_path)
    replacement = tmp_path / "unverified-wheel.tmp"
    with zipfile.ZipFile(replacement, "w") as archive:
        archive.writestr(
            "tf_build-0.1.0.dev0.dist-info/METADATA",
            "Metadata-Version: 2.3\nName: substituted-project\nVersion: 0.1.0.dev0\n",
        )
    original_check = manifest_module._check_package_identity
    replaced = False

    def swap_after_valid_metadata(payload: bytes, name: str, version: str, source: str) -> None:
        nonlocal replaced
        original_check(payload, name, version, source)
        if source == "wheel" and not replaced:
            os.replace(replacement, wheel)
            replaced = True

    monkeypatch.setattr(manifest_module, "_check_package_identity", swap_after_valid_metadata)
    with pytest.raises(WheelManifestError, match="changed|identity|metadata|wheel"):
        build_wheel_manifest(wheels, project, "a" * 40)
    assert replaced
    assert b"substituted-project" in zipfile.ZipFile(wheel).read(
        "tf_build-0.1.0.dev0.dist-info/METADATA"
    )


@pytest.mark.skipif(os.name != "posix", reason="atomic replace of open archive requires POSIX")
def test_sdist_manifest_rejects_replacement_after_embedded_metadata_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, wheels, sdist = _sdist_fixture(tmp_path)
    replacement = tmp_path / "unverified-source.tmp"
    body = b"Metadata-Version: 2.3\nName: tf-build\nVersion: 99.99.99\n"
    with tarfile.open(replacement, "w:gz") as tar:
        member = tarfile.TarInfo("tf_build-0.1.0rc1/PKG-INFO")
        member.size = len(body)
        tar.addfile(member, io.BytesIO(body))
    original_check = manifest_module._check_package_identity
    replaced = False

    def swap_after_valid_metadata(payload: bytes, name: str, version: str, source: str) -> None:
        nonlocal replaced
        original_check(payload, name, version, source)
        if source == "sdist" and not replaced:
            os.replace(replacement, sdist)
            replaced = True

    monkeypatch.setattr(manifest_module, "_check_package_identity", swap_after_valid_metadata)
    with pytest.raises(WheelManifestError, match="changed|identity|metadata|sdist"):
        build_wheel_manifest(
            wheels, project, "a" * 40, sdist_dir=sdist.parent,
            release_tag="v0.1.0rc1",
        )
    assert replaced
    with tarfile.open(sdist, "r:gz") as tar:
        meta = tar.extractfile("tf_build-0.1.0rc1/PKG-INFO")
        assert meta is not None
        assert b"99.99.99" in meta.read()


def test_release_manifest_json_serialization_failure_leaves_no_output(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "wheel-manifest.json"
    with pytest.raises(TypeError):
        write_wheel_manifest(destination, {"invalid": object()})
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_release_manifest_fsync_failure_cleans_unpublished_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "wheel-manifest.json"
    attempted = False

    def fail_sync(_fd: int) -> None:
        nonlocal attempted
        attempted = True
        raise OSError("simulated disk sync failure")

    monkeypatch.setattr(os, "fsync", fail_sync)
    with pytest.raises(OSError, match="sync failure"):
        write_wheel_manifest(destination, {"wheel": {"sha256": "a" * 64}})
    assert attempted, "release evidence must be flushed before publication"
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_release_manifest_concurrent_destination_cannot_be_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "wheel-manifest.json"
    original_link = os.link
    interposed = False
    competitor = b"existing competing release evidence"

    def conflict_on_publication(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
    ) -> None:
        nonlocal interposed
        if os.fspath(target) == os.fspath(destination):
            destination.write_bytes(competitor)
            interposed = True
        original_link(source, target)

    monkeypatch.setattr(os, "link", conflict_on_publication)
    with pytest.raises(FileExistsError):
        write_wheel_manifest(destination, {"source_commit": "a" * 40})
    assert interposed
    assert destination.read_bytes() == competitor
    assert list(tmp_path.iterdir()) == [destination]


def test_release_manifest_existing_symlink_is_never_replaced(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "do-not-touch.txt"
    outside.write_text("original", encoding="utf-8")
    destination = tmp_path / "wheel-manifest.json"
    destination.symlink_to(outside)
    with pytest.raises(FileExistsError):
        write_wheel_manifest(destination, {"schema": 1})
    assert destination.is_symlink()
    assert outside.read_text(encoding="utf-8") == "original"
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
        [outside.name, destination.name]
    )


@pytest.mark.skipif(os.name != "posix", reason="POSIX ctime semantics required")
def test_manifest_identity_rejects_same_inode_rewrite_after_hash_before_final_lstat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate.whl"
    original = b"A" * 4096
    replacement = b"B" * len(original)
    candidate.write_bytes(original)
    old_ns = 1_700_000_000_123_456_789
    os.utime(candidate, ns=(old_ns, old_ns))
    before = candidate.stat()
    original_sha256 = hashlib.sha256(original).hexdigest()

    native_lstat = Path.lstat
    observations = 0

    def overwrite_at_final_path_check(path: Path) -> os.stat_result:
        nonlocal observations
        if path == candidate:
            observations += 1
            if observations == 2:
                # The opened SHA256 FD was already closed. Mutate the very same
                # inode without changing size or the visible modification time.
                candidate.write_bytes(replacement)
                os.utime(candidate, ns=(old_ns, old_ns))
        return native_lstat(path)

    monkeypatch.setattr(Path, "lstat", overwrite_at_final_path_check)
    with pytest.raises(WheelManifestError, match="changed|identity"):
        manifest_module._identity(candidate)

    after = candidate.stat()
    assert observations == 2
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    )
    assert after.st_ctime_ns != before.st_ctime_ns
    assert candidate.read_bytes() == replacement
    assert hashlib.sha256(candidate.read_bytes()).hexdigest() != original_sha256
