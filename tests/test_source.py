from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tf_build.source import GitSourceError, validate_git_revision, verify_git_source


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
