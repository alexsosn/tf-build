from __future__ import annotations

import os
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Any, cast

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



def test_opt_in_git_verification_rejects_ignored_nonversioned_inputs(
    tmp_path: Path,
) -> None:
    repo, _ = _make_repo(tmp_path)
    (repo / ".gitignore").write_text("raw/\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "--quiet", "-m", "ignore fetched external inputs")
    revision = _git(repo, "rev-parse", "HEAD")
    (repo / "raw").mkdir()
    ignored_input = repo / "raw" / "input.tsv"
    ignored_input.write_text("externally downloaded source\n", encoding="utf-8")

    assert _git(
        repo, "status", "--porcelain=v1", "--untracked-files=all",
        "--ignore-submodules=none",
    ) == ""
    assert "raw/" in _git(
        repo, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory"
    )
    assert verify_git_source(repo, expected_revision=revision).revision == revision
    with pytest.raises(GitSourceError, match="ignored") as error:
        verify_git_source(
            repo, expected_revision=revision, reject_ignored_files=True
        )
    assert "raw/" not in str(error.value)
    assert "input.tsv" not in str(error.value)

    ignored_input.unlink()
    strict = verify_git_source(
        repo, expected_revision=revision, reject_ignored_files=True
    )
    assert strict.revision == revision



def test_strict_ignored_inventory_skips_empty_ignored_directories(
    tmp_path: Path,
) -> None:
    repo, _ = _make_repo(tmp_path)
    (repo / ".gitignore").write_text("raw/\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "--quiet", "-m", "exclude local data directory")
    revision = _git(repo, "rev-parse", "HEAD")
    (repo / "raw").mkdir()

    # Git's --directory without --no-empty-directory lists this empty folder.
    assert "raw/" in _git(
        repo, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory"
    )
    assert _git(
        repo, "ls-files", "--others", "--ignored", "--exclude-standard",
        "--directory", "--no-empty-directory",
    ) == ""
    checked = verify_git_source(repo, reject_ignored_files=True)
    assert checked.revision == revision



@pytest.mark.skipif(
    os.name == "nt", reason="Windows filesystems disallow whitespace-only filenames"
)
def test_strict_ignored_inventory_detects_whitespace_only_filenames(
    tmp_path: Path,
) -> None:
    repo, _ = _make_repo(tmp_path)
    (repo / ".gitignore").write_text("*\n", encoding="utf-8")
    _git(repo, "add", "-f", ".gitignore")
    _git(repo, "commit", "--quiet", "-m", "ignore all local data")
    ignored_file = repo / " "
    ignored_file.write_text("nonversioned input\n", encoding="utf-8")

    # The existing _run_git/.strip() collapses Git's " \n" output to "".
    assert _git(
        repo, "ls-files", "--others", "--ignored", "--exclude-standard",
        "--directory", "--no-empty-directory",
    ) == ""
    with pytest.raises(GitSourceError, match="ignored"):
        verify_git_source(repo, reject_ignored_files=True)


def test_strict_ignored_inventory_is_repository_wide_not_subdirectory_only(
    tmp_path: Path,
) -> None:
    repo, _ = _make_repo(tmp_path)
    selected = repo / "selected"
    selected.mkdir()
    (selected / "tracked.txt").write_text("selected input\n", encoding="utf-8")
    (repo / ".gitignore").write_text("raw/\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "selected/tracked.txt")
    _git(repo, "commit", "--quiet", "-m", "selected corpus")
    revision = _git(repo, "rev-parse", "HEAD")
    (repo / "raw").mkdir()
    (repo / "raw" / "references.txt").write_text("unversioned\n", encoding="utf-8")

    assert _git(
        selected, "ls-files", "--others", "--ignored", "--exclude-standard",
        "--directory",
    ) == ""
    assert verify_git_source(selected, expected_revision=revision).path == (
        selected.resolve()
    )
    with pytest.raises(GitSourceError, match="ignored") as error:
        verify_git_source(selected, reject_ignored_files=True)
    assert "references.txt" not in str(error.value)


@pytest.mark.parametrize("bad", [None, 0, 1, "true", 2.5])
def test_reject_ignored_files_option_requires_boolean_before_git_io(
    tmp_path: Path, bad: object
) -> None:
    with pytest.raises(ValueError, match="reject_ignored_files"):
        verify_git_source(
            tmp_path / "nonexistent", reject_ignored_files=bad  # type: ignore[arg-type]
        )


def test_ignored_git_inventory_respects_command_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, revision = _make_repo(tmp_path)
    native_run = subprocess.run
    seen: list[float] = []

    def observe_git(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if isinstance(command, list) and "ls-files" in command:
            assert "--ignored" in command
            seen.append(kwargs["timeout"])
        return cast(subprocess.CompletedProcess[str], native_run(*args, **kwargs))

    monkeypatch.setattr("tf_build.source.subprocess.run", observe_git)
    checked = verify_git_source(
        repo, expected_revision=revision, reject_ignored_files=True,
        timeout_seconds=7.5,
    )
    assert checked.revision == revision
    assert seen == [7.5]


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


def test_acquired_checkout_does_not_persist_credential_bearing_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, revision = _make_repo(tmp_path)
    destination = tmp_path / "acquired"
    secret = "TEST_PRIVATE_TOKEN_42"
    locator = f"https://alice:{secret}@example.invalid/project.git"
    global_config = tmp_path / "git-credentials-rewrite.conf"
    # This exercises the *real* Git transport offline. The scoped insteadOf
    # rewrite sends the token-bearing source URL to an actual local repo.
    subprocess.run(
        [
            "git", "config", "--file", str(global_config),
            f"url.{source}.insteadOf", locator,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))

    snapshot = fetch_git_source(locator, destination, revision=revision)
    assert snapshot.revision == revision
    assert _git(destination, "rev-parse", "HEAD") == revision
    assert _git(destination, "status", "--porcelain=v1") == ""
    assert _git(destination, "remote") == ""
    assert not (destination / ".git" / "FETCH_HEAD").exists()
    assert (destination / "tracked.txt").read_text(encoding="utf-8") == "initial\n"
    for path in (destination / ".git").rglob("*"):
        if path.is_file():
            assert secret.encode("ascii") not in path.read_bytes(), str(path)



@pytest.mark.parametrize(
    ("locator", "from_child"),
    [
        ("./repo-sha1", False),
        ("repo-sha1", False),
        ("../repo-sha1", True),
        ("./-source-repo", False),
    ],
)
def test_fetch_local_relative_git_repository_uses_caller_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    locator: str,
    from_child: bool,
) -> None:
    source, revision = _make_repo(tmp_path)
    if locator == "./-source-repo":
        moved = tmp_path / "-source-repo"
        source.rename(moved)
        source = moved
    caller = tmp_path / "caller" if from_child else tmp_path
    caller.mkdir(exist_ok=True)
    monkeypatch.chdir(caller)

    native_run = subprocess.run
    observed: list[list[str]] = []

    def capture_fetch(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if isinstance(command, list) and "fetch" in command:
            observed.append(command)
        return cast(subprocess.CompletedProcess[str], native_run(*args, **kwargs))

    monkeypatch.setattr("tf_build.source.subprocess.run", capture_fetch)
    output = tmp_path / "relative-copy"
    snapshot = fetch_git_source(locator, output, revision=revision)

    assert snapshot.revision == revision
    assert snapshot.path == output.resolve()
    assert (snapshot.path / "tracked.txt").read_text(encoding="utf-8") == "initial\n"
    assert len(observed) == 1
    command = observed[0]
    assert command[command.index("--") + 1] == str(source.resolve())
    assert command[-1] == revision


def test_missing_explicit_local_relative_repository_is_rejected_before_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    destination = tmp_path / "not-created-parent" / "snapshot"
    with pytest.raises(GitSourceError, match="relative local Git repository"):
        fetch_git_source("./not-an-existing-git-repo", destination, revision="a" * 40)
    assert not destination.parent.exists()


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



@pytest.mark.parametrize(
    "repository",
    [
        "--upload-pack=SECRET_COMMAND",
        "--all",
        "-q",
        "https://example.invalid/SECRET\x00source.git",
        "https://example.invalid/SECRET\nsource.git",
        "https://example.invalid/SECRET\tsource.git",
        "https://example.invalid/SECRET\x7fsource.git",
    ],
)
def test_git_fetch_locator_preflight_rejects_options_and_controls_without_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repository: str
) -> None:
    parent = tmp_path / "new-parent"
    destination = parent / "new-source"

    def forbidden_git(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise AssertionError("no Git command may run for an unsafe source locator")

    monkeypatch.setattr("tf_build.source.subprocess.run", forbidden_git)
    with pytest.raises(GitSourceError, match="Git repository locator") as caught:
        fetch_git_source(repository, destination, revision="a" * 40)
    assert "SECRET" not in str(caught.value)
    assert not parent.exists()


def test_fetch_pinned_commit_passes_explicit_git_end_of_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream, revision = _make_repo(tmp_path)
    native_run = subprocess.run
    observed: list[list[str]] = []

    def watch_git(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if isinstance(command, list) and "fetch" in command:
            observed.append(command)
        return cast(subprocess.CompletedProcess[str], native_run(*args, **kwargs))

    monkeypatch.setattr("tf_build.source.subprocess.run", watch_git)
    snapshot = fetch_git_source(str(upstream), tmp_path / "copied", revision=revision)
    assert snapshot.revision == revision
    assert (snapshot.path / "tracked.txt").read_text(encoding="utf-8") == "initial\n"
    assert len(observed) == 1
    fetch = observed[0]
    assert fetch.index("--") < fetch.index(str(upstream))


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


@pytest.mark.parametrize(
    "seconds",
    [0.0, -1.0, float("nan"), float("inf"), float("-inf"), True, "600"],
)
def test_invalid_git_timeout_fails_before_source_or_destination_mutation(
    tmp_path: Path, seconds: float
) -> None:
    destination = tmp_path / "acquired"
    with pytest.raises(ValueError, match="timeout"):
        fetch_git_source(
            "bad-credential:secret@example.invalid/repo",
            destination,
            revision="a" * 40,
            timeout_seconds=seconds,
        )
    assert not destination.exists()
    assert not tuple(tmp_path.glob(".acquired.tf-build-*"))
    with pytest.raises(ValueError, match="timeout"):
        verify_git_source(tmp_path / "missing", timeout_seconds=seconds)


def test_acquisition_timeout_cleans_staging_and_keeps_empty_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "acquired"
    destination.mkdir()
    native_run = subprocess.run
    invoked = []

    def stalled_fetch(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        assert isinstance(command, list)
        if "fetch" in command:
            assert kwargs.get("timeout") == 2.5
            invoked.append(tuple(command))
            raise subprocess.TimeoutExpired(command, 2.5)
        return cast(subprocess.CompletedProcess[str], native_run(*args, **kwargs))

    monkeypatch.setattr("tf_build.source.subprocess.run", stalled_fetch)
    with pytest.raises(GitSourceError, match="timed out") as caught:
        fetch_git_source(
            "https://secret-token@example.invalid/private.git",
            destination,
            revision="a" * 40,
            timeout_seconds=2.5,
        )
    assert isinstance(caught.value.__cause__, subprocess.TimeoutExpired)
    assert "secret-token" not in str(caught.value)
    assert invoked
    assert destination.is_dir()
    assert not any(destination.iterdir())
    assert not tuple(tmp_path.glob(".acquired.tf-build-*"))


def test_verification_timeout_is_enforced_and_avoids_argument_disclosure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    commands = []

    def stalled_inspection(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        assert kwargs.get("timeout") == 3.75
        commands.append(tuple(command))
        raise subprocess.TimeoutExpired(command, 3.75)

    monkeypatch.setattr("tf_build.source.subprocess.run", stalled_inspection)
    with pytest.raises(GitSourceError, match="timed out") as caught:
        verify_git_source(repo, timeout_seconds=3.75)
    assert isinstance(caught.value.__cause__, subprocess.TimeoutExpired)
    assert commands and "rev-parse" in commands[0]
    assert "3.75" in str(caught.value)


def test_fetch_and_verify_accept_custom_timeout_against_real_local_git(
    tmp_path: Path,
) -> None:
    source, revision = _make_repo(tmp_path)
    verified = verify_git_source(source, expected_revision=revision, timeout_seconds=10.0)
    assert verified.revision == revision
    acquired = fetch_git_source(
        str(source), tmp_path / "copy", revision=revision, timeout_seconds=10.0
    )
    assert acquired.revision == revision
    assert (acquired.path / "tracked.txt").read_text(encoding="utf-8") == "initial\n"



@pytest.mark.parametrize("mode", ["timeout", "exit", "oserror"])
def test_git_locator_failures_redact_credentials_in_formatted_tracebacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    secret = "SECRET_CREDENTIAL"
    repository = f"https://user:{secret}@example.invalid/private.git"
    destination = tmp_path / "acquired"
    destination.mkdir()
    native_run = subprocess.run

    def failed_remote(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        assert isinstance(command, list)
        if "remote" in command or "fetch" in command:
            if mode == "timeout":
                raise subprocess.TimeoutExpired(command, 2.0, stderr=f"{secret} stderr")
            if mode == "exit":
                raise subprocess.CalledProcessError(
                    128, command, stderr=f"{secret} stderr"
                )
            raise OSError(f"{secret} transport subprocess failure")
        return cast(subprocess.CompletedProcess[str], native_run(*args, **kwargs))

    monkeypatch.setattr("tf_build.source.subprocess.run", failed_remote)
    with pytest.raises(GitSourceError) as caught:
        fetch_git_source(repository, destination, revision="a" * 40, timeout_seconds=2.0)

    error = caught.value
    assert secret not in str(error)
    assert secret not in "".join(traceback.format_exception(error))
    if mode == "timeout":
        assert isinstance(error.__cause__, subprocess.TimeoutExpired)
        assert error.__cause__.timeout == 2.0
    if mode == "exit":
        assert isinstance(error.__cause__, subprocess.CalledProcessError)
        assert error.__cause__.returncode == 128
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
        timeout_seconds: float = 1800.0,
    ) -> source_module.SourceSnapshot:
        snapshot = real_verify(
            source_path,
            expected_revision=expected_revision,
            timeout_seconds=timeout_seconds,
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
    real_rmtree = shutil.rmtree

    def fail_staging_cleanup(
        path: str | Path,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        candidate = Path(path)
        if candidate.name.startswith(".acquired.tf-build-"):
            raise OSError("simulated cleanup failure")
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr("tf_build.source.shutil.rmtree", fail_staging_cleanup)

    with pytest.raises(GitSourceError, match="Git") as caught:
        fetch_git_source(
            str(tmp_path / "missing-repository"),
            destination,
            revision="a" * 40,
        )

    notes = getattr(caught.value, "__notes__", ())
    assert any("staging cleanup failed" in note for note in notes)
