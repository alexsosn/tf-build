"""Installed-wheel publication smoke must run the real example, not only import APIs."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.check_installed_wheel import check_distribution


@pytest.mark.parametrize(
    "example_source",
    [
        "raise SystemExit(17)\n",
        "print('{\"algorithm\": \"sha256\", \"digest\": \"made-up\", \"files\": 5}')\n",
    ],
)
def test_checker_rejects_broken_or_empty_example(
    tmp_path: Path, example_source: str
) -> None:
    fake_checkout = tmp_path / "checkout"
    examples = fake_checkout / "examples"
    examples.mkdir(parents=True)
    (examples / "tiny_tf_publication.py").write_text(example_source, encoding="utf-8")

    # The installed package in this pytest process is outside fake_checkout.
    # Old checker silently passes both cases because it never launches the example.
    with pytest.raises(RuntimeError, match="publication"):
        check_distribution(fake_checkout)


def test_checker_accepts_real_tiny_tf_publication_from_separate_checkout(
    tmp_path: Path,
) -> None:
    fake_checkout = tmp_path / "checkout"
    examples = fake_checkout / "examples"
    examples.mkdir(parents=True)
    actual_example = (
        Path(__file__).resolve().parents[1] / "examples" / "tiny_tf_publication.py"
    )
    shutil.copyfile(actual_example, examples / "tiny_tf_publication.py")
    check_distribution(fake_checkout)
