"""Contract tests derived from current Agora host and two TF materializers."""

from __future__ import annotations

from pathlib import Path

import pytest

from tf_build.agora import (
    AgoraOutputError,
    agora_output_path,
    optional_source_revision,
    prepare_agora_output,
)


def test_host_owned_empty_directory_is_checked_not_created(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    before = tuple(tmp_path.iterdir())

    assert prepare_agora_output(output) == output.resolve()
    assert tuple(tmp_path.iterdir()) == before
    assert tuple(output.iterdir()) == ()


def test_nonempty_missing_file_and_symlink_output_are_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(AgoraOutputError, match="output"):
        prepare_agora_output(missing)
    assert not missing.exists()

    file = tmp_path / "file"
    file.write_text("x")
    with pytest.raises(AgoraOutputError, match="output"):
        prepare_agora_output(file)

    directory = tmp_path / "directory"
    directory.mkdir()
    (directory / "existing.tf").write_text("x")
    with pytest.raises(AgoraOutputError, match="empty"):
        prepare_agora_output(directory)

    alias = tmp_path / "alias"
    alias.symlink_to(directory, target_is_directory=True)
    with pytest.raises(AgoraOutputError, match="symlink"):
        prepare_agora_output(alias)


def test_revision_optional_but_immutable_when_present() -> None:
    assert optional_source_revision("") is None
    assert optional_source_revision("ABCDEF01" * 5) == "abcdef01" * 5
    assert optional_source_revision("ABCDEF01" * 8) == "abcdef01" * 8


@pytest.mark.parametrize("revision", ["HEAD", "main", "ab012", "unversioned-local", " "])
def test_revision_rejects_nonempty_ambiguous_values(revision: str) -> None:
    with pytest.raises(AgoraOutputError, match="revision"):
        optional_source_revision(revision)


def test_direct_and_nested_tf_layouts_are_both_supported(tmp_path: Path) -> None:
    output = tmp_path / "agora-output"
    output.mkdir()
    root = prepare_agora_output(output)

    # Pseudepigrapha's TF files live immediately below the host output root.
    assert agora_output_path(root, "otype.tf") == output / "otype.tf"
    assert agora_output_path(root, "conversion-report.json") == (
        output / "conversion-report.json"
    )

    # CopticScriptorium-TF writes into a tf/ child and reports at root.
    assert agora_output_path(root, "tf") == output / "tf"
    assert agora_output_path(root, "tf/otype.tf") == output / "tf" / "otype.tf"
    assert agora_output_path(root, "conversion-summary.json") == (
        output / "conversion-summary.json"
    )


@pytest.mark.parametrize(
    "path",
    [
        "", ".", "..", "../outside", "tf/../outside", "tf/./otype.tf",
        "tf//otype.tf", "/tmp/otype.tf", "C:/output/otype.tf", "C:otype.tf",
        r"\\server\share", r"tf\otype.tf",
    ],
)
def test_output_relative_path_must_be_portable(tmp_path: Path, path: str) -> None:
    root = tmp_path / "output"
    root.mkdir()
    with pytest.raises(AgoraOutputError, match="path"):
        agora_output_path(root, path)


def test_reserved_host_receipt_cannot_be_written_by_converter(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(AgoraOutputError, match="reserved"):
        agora_output_path(output, "agora-materialization.json")
    assert agora_output_path(output, "conversion-report.json") == (
        output / "conversion-report.json"
    )


def test_symlinked_output_component_is_never_traversed(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "keep.txt"
    marker.write_text("safe")
    (output / "tf").symlink_to(outside, target_is_directory=True)

    with pytest.raises(AgoraOutputError, match="symlink"):
        agora_output_path(output, "tf/otype.tf")
    assert marker.read_text() == "safe"

    alias = tmp_path / "alias"
    alias.symlink_to(output, target_is_directory=True)
    with pytest.raises(AgoraOutputError, match="symlink"):
        agora_output_path(alias, "otype.tf")
