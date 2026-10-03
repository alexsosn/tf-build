from __future__ import annotations

from pathlib import Path

import pytest

from tf_build.workspace import BuildWorkspace, BuildWorkspaceError


def test_workspace_stages_beside_absent_destination(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with BuildWorkspace(destination) as workspace:
        staging = workspace.path
        assert staging.is_dir()
        assert staging.parent == tmp_path.resolve()
        assert staging.name.startswith(".artifact.tf-build-")
        assert workspace.destination == destination.resolve()
        assert not destination.exists()


def test_workspace_publishes_complete_staged_tree(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with BuildWorkspace(destination) as workspace:
        staging = workspace.path
        (staging / "otype.tf").write_text("otype\n", encoding="utf-8")
        nested = staging / "docs"
        nested.mkdir()
        (nested / "feature.md").write_text("docs\n", encoding="utf-8")

        published = workspace.publish()

        assert published == destination.resolve()
        assert (published / "otype.tf").read_text(encoding="utf-8") == "otype\n"
        assert (published / "docs" / "feature.md").read_text(encoding="utf-8") == "docs\n"
        assert not staging.exists()

    assert destination.is_dir()


def test_workspace_exit_without_publish_removes_staging(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with BuildWorkspace(destination) as workspace:
        staging = workspace.path
        (staging / "partial.tf").write_text("partial\n", encoding="utf-8")

    assert not staging.exists()
    assert not destination.exists()


def test_workspace_exception_before_publish_leaves_no_artifact(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with pytest.raises(RuntimeError, match="validation failed"):
        with BuildWorkspace(destination) as workspace:
            staging = workspace.path
            (staging / "partial.tf").write_text("partial\n", encoding="utf-8")
            raise RuntimeError("validation failed")

    assert not staging.exists()
    assert not destination.exists()


@pytest.mark.parametrize("kind", ["empty-dir", "nonempty-dir", "file", "symlink", "dangling"])
def test_workspace_rejects_existing_destination(tmp_path: Path, kind: str) -> None:
    destination = tmp_path / "artifact"

    if kind in {"empty-dir", "nonempty-dir"}:
        destination.mkdir()
        if kind == "nonempty-dir":
            (destination / "sentinel").write_text("keep\n", encoding="utf-8")
    elif kind == "file":
        destination.write_text("keep\n", encoding="utf-8")
    else:
        target = tmp_path / "target"
        if kind == "symlink":
            target.mkdir()
        try:
            destination.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks are unavailable on this platform")

    with pytest.raises(FileExistsError):
        with BuildWorkspace(destination):
            pass

    if kind in {"symlink", "dangling"}:
        assert destination.is_symlink()
    else:
        assert destination.exists()


def test_workspace_does_not_clobber_destination_created_before_publish(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "artifact"

    with BuildWorkspace(destination) as workspace:
        staging = workspace.path
        (staging / "payload.tf").write_text("payload\n", encoding="utf-8")

        destination.mkdir()
        before = destination.stat()

        with pytest.raises(FileExistsError):
            workspace.publish()

        after = destination.stat()
        assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
        assert staging.is_dir()
        assert (staging / "payload.tf").is_file()

    assert destination.is_dir()
    assert not any(destination.iterdir())
    assert not staging.exists()


def test_workspace_publish_is_single_use(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with BuildWorkspace(destination) as workspace:
        workspace.publish()
        with pytest.raises(BuildWorkspaceError, match="active"):
            workspace.publish()


def test_workspace_path_is_unavailable_outside_active_context(tmp_path: Path) -> None:
    workspace = BuildWorkspace(tmp_path / "artifact")

    with pytest.raises(BuildWorkspaceError, match="active"):
        _ = workspace.path

    with workspace:
        staging = workspace.path
        assert staging.is_dir()

    with pytest.raises(BuildWorkspaceError, match="active"):
        _ = workspace.path


def test_workspace_creates_and_resolves_missing_parent(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "deeper" / "artifact"

    with BuildWorkspace(destination) as workspace:
        assert workspace.destination == destination.resolve()
        assert workspace.path.parent == destination.parent.resolve()


def test_workspace_never_reuses_unpublished_staging(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with BuildWorkspace(destination) as first:
        old_staging = first.path
        (old_staging / "obsolete.tf").write_text("obsolete\n", encoding="utf-8")

    assert not old_staging.exists()

    with BuildWorkspace(destination) as second:
        assert not (second.path / "obsolete.tf").exists()
        (second.path / "current.tf").write_text("current\n", encoding="utf-8")
        second.publish()

    assert not (destination / "obsolete.tf").exists()
    assert (destination / "current.tf").is_file()



def test_workspace_surfaces_cleanup_failure_without_primary_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "artifact"

    def fail_cleanup(path: Path) -> None:
        raise OSError("cleanup denied")

    with pytest.raises(BuildWorkspaceError, match="cleanup"):
        with BuildWorkspace(destination) as workspace:
            staging = workspace.path
            monkeypatch.setattr("tf_build.workspace.shutil.rmtree", fail_cleanup)

    assert staging.exists()
    assert not destination.exists()


def test_workspace_preserves_primary_exception_and_notes_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "artifact"

    def fail_cleanup(path: Path) -> None:
        raise OSError("cleanup denied")

    with pytest.raises(RuntimeError, match="build failed") as caught:
        with BuildWorkspace(destination) as workspace:
            staging = workspace.path
            monkeypatch.setattr("tf_build.workspace.shutil.rmtree", fail_cleanup)
            raise RuntimeError("build failed")

    assert staging.exists()
    notes = getattr(caught.value, "__notes__", ())
    assert any("cleanup" in note for note in notes)
