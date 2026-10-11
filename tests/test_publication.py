"""Public path publisher contract, exercised on actual filesystem inodes."""

from __future__ import annotations

import errno
import sys
from pathlib import Path

import pytest

from tf_build.publication import publish_path_no_clobber


def _stage(tmp_path: Path) -> Path:
    source = tmp_path / "private-stage"
    source.mkdir()
    (source / "sentinel").write_bytes(b"validated artifact bytes")
    return source


def test_public_publisher_moves_validated_tree_to_absent_destination(
    tmp_path: Path,
) -> None:
    stage = _stage(tmp_path)
    output = tmp_path / "published"
    old_inode = stage.stat().st_ino

    publish_path_no_clobber(stage, output)

    assert not stage.exists()
    assert output.is_dir()
    assert output.stat().st_ino == old_inode
    assert (output / "sentinel").read_bytes() == b"validated artifact bytes"


@pytest.mark.parametrize(
    "kind",
    ["empty-directory", "nonempty-directory", "file", "symlink", "dangling-symlink"],
)
def test_public_publisher_never_clobbers_existing_target(
    tmp_path: Path, kind: str
) -> None:
    stage = _stage(tmp_path)
    output = tmp_path / "published"
    if kind.endswith("directory"):
        output.mkdir()
        if kind == "nonempty-directory":
            (output / "keep").write_bytes(b"leave me")
    elif kind == "file":
        output.write_bytes(b"existing file")
    else:
        target = tmp_path / "link_target"
        if kind == "symlink":
            target.mkdir()
        try:
            output.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("cannot create test symlink")

    old_lstat = output.lstat()
    old_files = (
        tuple(sorted(x.name for x in output.iterdir()))
        if output.is_dir() and not output.is_symlink()
        else ()
    )
    with pytest.raises(FileExistsError):
        publish_path_no_clobber(stage, output)

    assert (output.lstat().st_dev, output.lstat().st_ino) == (
        old_lstat.st_dev, old_lstat.st_ino
    )
    assert stage.is_dir()
    assert (stage / "sentinel").read_bytes() == b"validated artifact bytes"
    if kind.endswith("directory"):
        assert tuple(sorted(x.name for x in output.iterdir())) == old_files
    elif kind == "file":
        assert output.read_bytes() == b"existing file"
    else:
        assert output.is_symlink()


def test_public_publisher_does_not_create_target_when_source_is_missing(
    tmp_path: Path,
) -> None:
    stage = tmp_path / "missing-stage"
    output = tmp_path / "published"

    with pytest.raises(OSError) as caught:
        publish_path_no_clobber(stage, output)

    assert caught.value.errno in {errno.ENOENT, errno.ENOTDIR}
    assert not output.exists()


def test_public_path_publisher_is_same_implementation_as_workspace_uses() -> None:
    from tf_build import _atomic

    assert publish_path_no_clobber is _atomic.publish_path_no_clobber


def test_public_publisher_moves_file_without_changing_bytes(tmp_path: Path) -> None:
    source = tmp_path / "artifact.json"
    destination = tmp_path / "published.json"
    source.write_bytes(b'{"valid":true}')
    old_inode = source.stat().st_ino

    publish_path_no_clobber(source, destination)

    assert not source.exists()
    assert destination.read_bytes() == b'{"valid":true}'
    assert destination.stat().st_ino == old_inode


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="Linux renameat2 symbol availability",
)
def test_public_publisher_fails_closed_when_atomic_rename_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _stage(tmp_path)
    destination = tmp_path / "published"
    monkeypatch.setattr(
        "tf_build._atomic.ctypes.CDLL", lambda *args, **kwargs: object()
    )

    with pytest.raises(OSError, match="unsupported"):
        publish_path_no_clobber(source, destination)

    assert source.is_dir()
    assert (source / "sentinel").read_bytes() == b"validated artifact bytes"
    assert not destination.exists()
