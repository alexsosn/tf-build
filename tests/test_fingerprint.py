"""Raw-byte fingerprint contract tests using real filesystem trees."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from tf_build.fingerprint import FingerprintError, fingerprint_tree


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "artifact"
    root.mkdir()
    return root


def test_same_bytes_and_names_have_stable_tree_identity(tmp_path: Path) -> None:
    one = _root(tmp_path)
    (one / "b.tf").write_bytes(b"beta")
    (one / "a.tf").write_bytes(b"alpha")

    two = tmp_path / "other"
    two.mkdir()
    (two / "a.tf").write_bytes(b"alpha")
    (two / "b.tf").write_bytes(b"beta")

    a = fingerprint_tree(one)
    b = fingerprint_tree(two)

    assert a == b
    assert a.algorithm == "tf-build-tree-sha256-v1"
    assert tuple(item.path for item in a.files) == ("a.tf", "b.tf")
    assert a.files[0].sha256 == "sha256:" + hashlib.sha256(b"alpha").hexdigest()


def test_byte_change_is_not_normalized_even_for_tf_timestamp(tmp_path: Path) -> None:
    root = _root(tmp_path)
    path = root / "otype.tf"
    path.write_bytes(b"@valueType=str\n@dateWritten=one\n\n1\tword\n")
    before = fingerprint_tree(root)
    path.write_bytes(b"@valueType=str\n@dateWritten=two\n\n1\tword\n")
    after = fingerprint_tree(root)

    assert before.digest != after.digest
    assert before.files[0].sha256 != after.files[0].sha256


def test_add_remove_rename_and_non_tf_bytes_change_identity(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "otype.tf").write_bytes(b"tf")
    first = fingerprint_tree(root).digest
    (root / "LICENSE").write_bytes(b"license")
    second = fingerprint_tree(root).digest
    assert second != first
    (root / "LICENSE").rename(root / "COPYING")
    third = fingerprint_tree(root).digest
    assert third != second
    (root / "COPYING").unlink()
    assert fingerprint_tree(root).digest == first


def test_nested_and_empty_files_and_empty_tree_have_defined_identity(tmp_path: Path) -> None:
    root = _root(tmp_path)
    empty = fingerprint_tree(root)
    assert empty.files == ()
    assert empty.digest.startswith("sha256:")

    nested = root / "module" / "nested"
    nested.mkdir(parents=True)
    (nested / "empty.tf").write_bytes(b"")
    result = fingerprint_tree(root)
    assert [(item.path, item.size) for item in result.files] == [
        ("module/nested/empty.tf", 0)
    ]
    assert result.digest != empty.digest


def test_compiled_cache_is_excluded_but_normal_sibling_files_count(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "otype.tf").write_bytes(b"otype")
    baseline = fingerprint_tree(root)
    cache = root / ".tf" / "cache-version"
    cache.mkdir(parents=True)
    (cache / "otype.tfx").write_bytes(b"compiled")
    assert fingerprint_tree(root) == baseline
    (root / "cache-version").write_bytes(b"not-derived")
    assert fingerprint_tree(root).digest != baseline.digest


def test_only_explicit_manifest_is_excluded(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "otype.tf").write_bytes(b"otype")
    (root / "BUILD-MANIFEST.json").write_bytes(b"v1")
    (root / "OTHER-MANIFEST.json").write_bytes(b"v1")
    before = fingerprint_tree(root, manifest_path="BUILD-MANIFEST.json")
    (root / "BUILD-MANIFEST.json").write_bytes(b"v2")
    assert fingerprint_tree(root, manifest_path="BUILD-MANIFEST.json") == before
    assert fingerprint_tree(root).digest != fingerprint_tree(
        root, manifest_path="BUILD-MANIFEST.json"
    ).digest
    (root / "OTHER-MANIFEST.json").write_bytes(b"v2")
    assert fingerprint_tree(root, manifest_path="BUILD-MANIFEST.json").digest != before.digest



@pytest.mark.parametrize("excluded", [".tf", "module/.tf"])
def test_manifest_cannot_exclude_compiled_cache_directory(
    tmp_path: Path, excluded: str
) -> None:
    root = _root(tmp_path)
    (root / "module" / ".tf").mkdir(parents=True)
    (root / ".tf").mkdir()
    with pytest.raises(FingerprintError, match="manifest"):
        fingerprint_tree(root, manifest_path=excluded)

def test_symlinks_are_rejected_without_following(tmp_path: Path) -> None:
    root = _root(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "data").write_bytes(b"do not touch")
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(FingerprintError, match="symlink"):
        fingerprint_tree(alias)

    (root / "linked-file").symlink_to(outside / "data")
    with pytest.raises(FingerprintError, match="symlink"):
        fingerprint_tree(root)
    (root / "linked-file").unlink()

    (root / "linked-dir").symlink_to(outside, target_is_directory=True)
    with pytest.raises(FingerprintError, match="symlink"):
        fingerprint_tree(root)
    (root / "linked-dir").unlink()

    (root / ".tf").symlink_to(outside, target_is_directory=True)
    with pytest.raises(FingerprintError, match="symlink"):
        fingerprint_tree(root)
    assert (outside / "data").read_bytes() == b"do not touch"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO unavailable")
def test_nonregular_entries_are_rejected(tmp_path: Path) -> None:
    root = _root(tmp_path)
    os.mkfifo(root / "fifo")
    with pytest.raises(FingerprintError, match="regular"):
        fingerprint_tree(root)


@pytest.mark.parametrize(
    "path",
    ["", ".", "..", "../MANIFEST", "/tmp/MANIFEST", "C:/MANIFEST",
     "C:MANIFEST", "dir/../MANIFEST", "dir\\MANIFEST"],
)
def test_manifest_exclusion_requires_safe_logical_path(tmp_path: Path, path: str) -> None:
    root = _root(tmp_path)
    with pytest.raises(FingerprintError, match="manifest"):
        fingerprint_tree(root, manifest_path=path)


def test_aggregate_hash_has_length_framed_domain_separated_oracle(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "a.tf").write_bytes(b"z")
    result = fingerprint_tree(root)

    name = b"a.tf"
    payload = b"z"
    expected = hashlib.sha256(
        b"tf-build-tree-sha256-v1\x00"
        + len(name).to_bytes(8, "big")
        + name
        + len(payload).to_bytes(8, "big")
        + hashlib.sha256(payload).digest()
    ).hexdigest()

    assert result.digest == "sha256:" + expected
    assert result.files[0].size == 1
