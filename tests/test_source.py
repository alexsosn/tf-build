from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

import tf_build.source as source_module
from tf_build.source import (
    GitSourceError,
    fetch_git_source,
    validate_git_revision,
    verify_git_source,
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _make_repo(tmp_path: Path, *, object_format: str = "sha1") -> tuple[Path, str]:
    repo = tmp_path / f"repo-{object_format}"
    repo.mkdir()
    init = ["init", "--quiet"]
    if object_format == "sha256":
        init.insert(1, "--object-format=sha256")
    _git(repo, *init)
    _git(repo, "config", "user.email", "tf-build@example.invalid")
    _git(repo, "config", "user.name", "tf-build tests")
    (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "--quiet", "-m", "initial")
    return repo, _git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    ("revision", "expected"),
    [
        ("a" * 40, "a" * 40),
        ("ABCDEF0123456789ABCDEF0123456789ABCDEF01", "abcdef0123456789abcdef0123456789abcdef01"),
        ("b" * 64, "b" * 64),
        ("ABCDEF01" * 8, ("abcdef01" * 8)),
    ],
)
def test_validate_git_revision_accepts_full_sha1_and_sha256(
    revision: str, expected: str
) -> None:
    assert validate_git_revision(revision) == expected


@pytest.mark.parametrize(
    "revision",
    [
        "main",
        "HEAD",
        "v1.0",
        "abcdef0",
        "g" * 40,
        "0" * 39,
        "0" * 41,
        "0" * 63,
        "0" * 65,
        "",
    ],
)
def test_validate_git_revision_rejects_ambiguous_or_invalid_values(revision: str) -> None:
    with pytest.raises(GitSourceError, match="full 40- or 64-hex"):
        validate_git_revision(revision)


def test_verify_git_source_accepts_clean_sha1_checkout(tmp_path: Path) -> None:
    repo, revision = _make_repo(tmp_path)

    snapshot = verify_git_source(repo, expected_revision=revision.upper())

    assert snapshot.path == repo.resolve()
    assert snapshot.repository_root == repo.resolve()
    assert snapshot.revision == revision
    assert snapshot.object_format == "sha1"


def test_verify_git_source_accepts_clean_sha256_checkout(tmp_path: Path) -> None:
    try:
        repo, revision = _make_repo(tmp_path, object_format="sha256")
    except subprocess.CalledProcessError:
        pytest.skip("installed Git does not support SHA-256 repositories")

    snapshot = verify_git_source(repo, expected_revision=revision.upper())

    assert len(revision) == 64
    assert snapshot.revision == revision
    assert snapshot.object_format == "sha256"


def test_verify_git_source_rejects_revision_mismatch(tmp_path: Path) -> None:
    repo, revision = _make_repo(tmp_path)
    wrong = ("0" if revision[0] != "0" else "1") + revision[1:]

    with pytest.raises(GitSourceError, match="revision mismatch"):
        verify_git_source(repo, expected_revision=wrong)


@pytest.mark.parametrize("kind", ["tracked", "staged", "untracked"])
def test_verify_git_source_rejects_dirty_checkout(tmp_path: Path, kind: str) -> None:
    repo, revision = _make_repo(tmp_path)

    if kind == "tracked":
        (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    elif kind == "staged":
        (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        _git(repo, "add", "tracked.txt")
    else:
        (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")

    with pytest.raises(GitSourceError, match="dirty"):
        verify_git_source(repo, expected_revision=revision)


def test_verify_git_source_rejects_non_git_directory(tmp_path: Path) -> None:
    source = tmp_path / "plain"
    source.mkdir()

    with pytest.raises(GitSourceError, match="Git"):
        verify_git_source(source)


def test_verify_git_source_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(GitSourceError, match="does not exist"):
        verify_git_source(tmp_path / "missing")


def test_verify_git_source_records_selected_subdirectory_and_repo_root(
    tmp_path: Path,
) -> None:
    repo, revision = _make_repo(tmp_path)
    selected = repo / "source"
    selected.mkdir()
    _git(repo, "add", "source")
    # Git does not track empty directories; the clean checkout is unchanged.

    snapshot = verify_git_source(selected, expected_revision=revision)

    assert snapshot.path == selected.resolve()
    assert snapshot.repository_root == repo.resolve()


def test_fetch_git_source_acquires_exact_sha1_to_new_destination(tmp_path: Path) -> None:
    source, revision = _make_repo(tmp_path)
    destination = tmp_path / "acquired"

    snapshot = fetch_git_source(str(source), destination, revision=revision.upper())

    assert snapshot.path == destination.resolve()
    assert snapshot.repository_root == destination.resolve()
    assert snapshot.revision == revision
    assert snapshot.object_format == "sha1"
    assert (destination / "tracked.txt").read_text(encoding="utf-8") == "initial\n"
    assert _git(destination, "status", "--porcelain", "--untracked-files=all") == ""
    detached = subprocess.run(
        ["git", "-C", str(destination), "symbolic-ref", "-q", "HEAD"],
        capture_output=True,
        text=True,
    )
    assert detached.returncode != 0


def test_fetch_git_source_replaces_preexisting_empty_destination(tmp_path: Path) -> None:
    source, revision = _make_repo(tmp_path)
    destination = tmp_path / "acquired"
    destination.mkdir()

    snapshot = fetch_git_source(str(source), destination, revision=revision)

    assert snapshot.path == destination.resolve()
    assert (destination / "tracked.txt").is_file()


def test_fetch_git_source_supports_sha256_repository(tmp_path: Path) -> None:
    try:
        source, revision = _make_repo(tmp_path, object_format="sha256")
    except subprocess.CalledProcessError:
        pytest.skip("installed Git does not support SHA-256 repositories")
    destination = tmp_path / "acquired-sha256"

    snapshot = fetch_git_source(str(source), destination, revision=revision)

    assert snapshot.revision == revision
    assert snapshot.object_format == "sha256"
    assert _git(destination, "rev-parse", "--show-object-format") == "sha256"


@pytest.mark.parametrize("revision", ["main", "HEAD", "abcdef0"])
def test_fetch_git_source_rejects_ambiguous_revision_before_destination_change(
    tmp_path: Path, revision: str
) -> None:
    destination = tmp_path / "acquired"

    with pytest.raises(GitSourceError, match="full 40- or 64-hex"):
        fetch_git_source("/definitely/not/a/repository", destination, revision=revision)

    assert not destination.exists()


def test_fetch_git_source_rejects_empty_repository_locator(tmp_path: Path) -> None:
    destination = tmp_path / "acquired"

    with pytest.raises(GitSourceError, match="repository"):
        fetch_git_source("", destination, revision="a" * 40)

    assert not destination.exists()


def test_fetch_git_source_rejects_nonempty_destination(tmp_path: Path) -> None:
    source, revision = _make_repo(tmp_path)
    destination = tmp_path / "acquired"
    destination.mkdir()
    sentinel = destination / "sentinel"
    sentinel.write_text("keep\n", encoding="utf-8")

    with pytest.raises(GitSourceError, match="not empty"):
        fetch_git_source(str(source), destination, revision=revision)

    assert sentinel.read_text(encoding="utf-8") == "keep\n"


def test_fetch_git_source_rejects_file_destination(tmp_path: Path) -> None:
    source, revision = _make_repo(tmp_path)
    destination = tmp_path / "acquired"
    destination.write_text("keep\n", encoding="utf-8")

    with pytest.raises(GitSourceError, match="not a directory"):
        fetch_git_source(str(source), destination, revision=revision)

    assert destination.read_text(encoding="utf-8") == "keep\n"


@pytest.mark.parametrize("dangling", [False, True])
def test_fetch_git_source_rejects_symlink_destination(
    tmp_path: Path, dangling: bool
) -> None:
    source, revision = _make_repo(tmp_path)
    target = tmp_path / "target"
    if not dangling:
        target.mkdir()
    destination = tmp_path / "acquired"
    destination.symlink_to(target, target_is_directory=True)

    with pytest.raises(GitSourceError, match="symlink"):
        fetch_git_source(str(source), destination, revision=revision)

    assert destination.is_symlink()


def test_fetch_git_source_failure_leaves_nonexistent_destination_absent(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "acquired"

    with pytest.raises(GitSourceError, match="Git"):
        fetch_git_source(
            str(tmp_path / "missing-repository"),
            destination,
            revision="a" * 40,
        )

    assert not destination.exists()
    assert not tuple(tmp_path.glob(".acquired.tf-build-*"))


def test_fetch_git_source_failure_preserves_preexisting_empty_destination(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "acquired"
    destination.mkdir()

    with pytest.raises(GitSourceError, match="Git"):
        fetch_git_source(
            str(tmp_path / "missing-repository"),
            destination,
            revision="a" * 40,
        )

    assert destination.is_dir()
    assert not any(destination.iterdir())
    assert not tuple(tmp_path.glob(".acquired.tf-build-*"))

def test_fetch_git_source_does_not_clobber_destination_created_before_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, revision = _make_repo(tmp_path)
    destination = tmp_path / "acquired"
    real_verify = source_module.verify_git_source

    def verify_then_race(
        source_path: str | Path,
        *,
        expected_revision: str | None = None,
    ) -> source_module.SourceSnapshot:
        snapshot = real_verify(
            source_path,
            expected_revision=expected_revision,
        )
        destination.mkdir()
        return snapshot

    monkeypatch.setattr(source_module, "verify_git_source", verify_then_race)

    with pytest.raises(FileExistsError):
        source_module.fetch_git_source(
            str(source),
            destination,
            revision=revision,
        )

    assert destination.is_dir()
    assert not any(destination.iterdir())
    assert not tuple(tmp_path.glob(".acquired.tf-build-*"))


def test_fetch_git_source_surfaces_staging_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "acquired"
    real_rmtree = source_module.shutil.rmtree

    def fail_staging_cleanup(
        path: str | Path,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        candidate = Path(path)
        if candidate.name.startswith(".acquired.tf-build-"):
            raise OSError("simulated cleanup failure")
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(source_module.shutil, "rmtree", fail_staging_cleanup)

    with pytest.raises(GitSourceError, match="Git") as caught:
        fetch_git_source(
            str(tmp_path / "missing-repository"),
            destination,
            revision="a" * 40,
        )

    notes = getattr(caught.value, "__notes__", ())
    assert any("staging cleanup failed" in note for note in notes)
