"""Contract tests for the public no-clobber publication primitive."""

from __future__ import annotations

from pathlib import Path

import pytest

from tf_build.publish import publish_path_no_clobber


def test_publish_directory_to_absent_target_keeps_complete_tree(tmp_path: Path) -> None:
    stage = tmp_path / "staging"
    stage.mkdir()
    nested = stage / "tf"
    nested.mkdir()
    (nested / "otype.tf").write_bytes(b"@node\\n@valueType=str\\n\\n1\\tword\\n")
    (stage / "conversion-summary.json").write_text('{"ok":true}\\n', encoding="utf-8")
    final = tmp_path / "published"

    publish_path_no_clobber(stage, final)

    assert not stage.exists()
    assert (final / "tf" / "otype.tf").read_bytes().startswith(b"@node")
    assert (final / "conversion-summary.json").read_text(encoding="utf-8") == (
        '{"ok":true}\\n'
    )


def test_publish_refuses_concurrently_created_empty_target_inode(tmp_path: Path) -> None:
    stage = tmp_path / "staging"
    stage.mkdir()
    (stage / "feature.tf").write_bytes(b"source bytes")
    destination = tmp_path / "published"

    # The competitor appears AFTER staging is complete and BEFORE publishing.
    destination.mkdir()
    competing = destination.stat()

    with pytest.raises(FileExistsError):
        publish_path_no_clobber(stage, destination)

    actual = destination.stat()
    assert (actual.st_dev, actual.st_ino) == (competing.st_dev, competing.st_ino)
    assert not any(destination.iterdir())
    assert (stage / "feature.tf").read_bytes() == b"source bytes"


@pytest.mark.parametrize("kind", ["nonempty-directory", "file", "symlink"])
def test_publish_rejects_existing_target_without_mutation(
    tmp_path: Path, kind: str
) -> None:
    stage = tmp_path / "staging"
    stage.mkdir()
    (stage / "feature.tf").write_bytes(b"unpublished")
    destination = tmp_path / "published"

    if kind == "nonempty-directory":
        destination.mkdir()
        (destination / "sentinel").write_text("original", encoding="utf-8")
    elif kind == "file":
        destination.write_text("original", encoding="utf-8")
    else:
        target = tmp_path / "target"
        target.mkdir()
        try:
            destination.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable")

    with pytest.raises(FileExistsError):
        publish_path_no_clobber(stage, destination)

    assert (stage / "feature.tf").read_bytes() == b"unpublished"
    if kind == "nonempty-directory":
        assert (destination / "sentinel").read_text(encoding="utf-8") == "original"
    elif kind == "file":
        assert destination.read_text(encoding="utf-8") == "original"
    else:
        assert destination.is_symlink()


def test_publish_regular_file_to_absent_destination(tmp_path: Path) -> None:
    stage = tmp_path / "staging.bin"
    stage.write_bytes(b"raw release artifact")
    destination = tmp_path / "published.bin"

    publish_path_no_clobber(str(stage), str(destination))

    assert not stage.exists()
    assert destination.read_bytes() == b"raw release artifact"
