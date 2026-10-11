"""RED-first direct-vs-sdist rebuilt wheel package-byte parity tests."""

from __future__ import annotations

import stat
import zipfile
from pathlib import Path

import pytest

from scripts.compare_wheel_payloads import (
    WheelPayloadMismatch,
    compare_wheel_payloads,
    main,
)


def _wheel(
    path: Path,
    *,
    modules: dict[str, bytes] | None = None,
    metadata: bytes = b"original metadata",
    extra: tuple[str, bytes] | None = None,
    symlink: bool = False,
) -> Path:
    contents = modules if modules is not None else {
        "tf_build/__init__.py": b"from __future__ import annotations\n",
        "tf_build/source.py": b"REVISION = 42\n",
        "tf_build/nested/helper.py": b"def value(): return 1\n",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in contents.items():
            member = zipfile.ZipInfo(name, date_time=(2024, 1, 1, 0, 0, 0))
            member.create_system = 3
            if symlink and name == "tf_build/source.py":
                member.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(member, data)
        archive.writestr("tf_build-0.1.0rc1.dist-info/METADATA", metadata)
        if extra is not None:
            archive.writestr(*extra)
    return path


def test_identical_package_files_ignore_wheel_metadata_and_container_differences(
    tmp_path: Path,
) -> None:
    direct = _wheel(tmp_path / "direct.whl")
    rebuilt = _wheel(tmp_path / "rebuilt.whl", metadata=b"rebuilt metadata")
    assert compare_wheel_payloads(direct, rebuilt) == (
        "tf_build/__init__.py",
        "tf_build/nested/helper.py",
        "tf_build/source.py",
    )


@pytest.mark.parametrize(
    ("changed", "match"),
    [
        ({"tf_build/source.py": b"REVISION = 99\n"}, "tf_build/source.py"),
        ({"tf_build/source.py": None}, "tf_build/source.py"),
        ({"tf_build/new.py": b"secret change"}, "tf_build/new.py"),
    ],
)
def test_payload_differences_are_rejected(
    tmp_path: Path, changed: dict[str, bytes | None], match: str
) -> None:
    direct = _wheel(tmp_path / "direct.whl")
    contents: dict[str, bytes] = {
        "tf_build/__init__.py": b"from __future__ import annotations\n",
        "tf_build/source.py": b"REVISION = 42\n",
        "tf_build/nested/helper.py": b"def value(): return 1\n",
    }
    for name, replacement in changed.items():
        if replacement is None:
            del contents[name]
        else:
            contents[name] = replacement
    rebuilt = _wheel(tmp_path / "rebuilt.whl", modules=contents)
    with pytest.raises(WheelPayloadMismatch, match=match.replace(".", r"\.")):
        compare_wheel_payloads(direct, rebuilt)


@pytest.mark.parametrize(
    ("extra", "symlink"),
    [
        (("../escape.py", b"escape"), False),
        (("tf_build/../../escape.py", b"escape"), False),
        (("tf_build\\hidden.py", b"escape"), False),
        (("scripts/unsafe.py", b"escape"), False),
        (None, True),
    ],
)
def test_malicious_or_unexpected_wheel_contents_rejected(
    tmp_path: Path, extra: tuple[str, bytes] | None, symlink: bool
) -> None:
    good = _wheel(tmp_path / "good.whl")
    bad = _wheel(tmp_path / "bad.whl", extra=extra, symlink=symlink)
    with pytest.raises(WheelPayloadMismatch):
        compare_wheel_payloads(good, bad)


def test_duplicate_member_cannot_hide_package_change(tmp_path: Path) -> None:
    good = _wheel(tmp_path / "good.whl")
    duplicate = tmp_path / "duplicate.whl"
    _wheel(duplicate)
    with zipfile.ZipFile(duplicate, "a") as archive:
        archive.writestr("tf_build/source.py", b"altered second copy")
    with pytest.raises(WheelPayloadMismatch, match="duplicate"):
        compare_wheel_payloads(good, duplicate)


def test_missing_initializer_is_not_a_valid_package(tmp_path: Path) -> None:
    direct = _wheel(tmp_path / "direct.whl")
    incomplete = _wheel(
        tmp_path / "incomplete.whl", modules={"tf_build/source.py": b"code"}
    )
    with pytest.raises(WheelPayloadMismatch, match="__init__"):
        compare_wheel_payloads(direct, incomplete)


def test_directory_selection_rejects_ambiguous_and_missing_wheels(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    direct = tmp_path / "direct"
    rebuilt = tmp_path / "rebuilt"
    direct.mkdir()
    rebuilt.mkdir()
    _wheel(direct / "tf_build-0.1.0rc1-py3-none-any.whl")
    _wheel(rebuilt / "tf_build-0.1.0rc1-py3-none-any.whl")
    assert main(["--direct-dir", str(direct), "--rebuilt-dir", str(rebuilt)]) == 0
    assert "3 package files" in capsys.readouterr().out
    _wheel(rebuilt / "second.whl")
    with pytest.raises(WheelPayloadMismatch, match="exactly one"):
        main(["--direct-dir", str(direct), "--rebuilt-dir", str(rebuilt)])
    (rebuilt / "second.whl").unlink()
    (rebuilt / "tf_build-0.1.0rc1-py3-none-any.whl").unlink()
    with pytest.raises(WheelPayloadMismatch, match="exactly one"):
        main(["--direct-dir", str(direct), "--rebuilt-dir", str(rebuilt)])


@pytest.mark.parametrize(
    "workflow",
    [".github/workflows/ci.yml", ".github/workflows/release.yml"],
)
def test_each_distribution_workflow_gates_sdist_rebuild_before_wheel_smoke(
    workflow: str,
) -> None:
    path = Path(__file__).resolve().parents[1] / workflow
    text = path.read_text(encoding="utf-8")
    check = "scripts/compare_wheel_payloads.py"
    assert check in text
    assert text.index("sdist-wheels") < text.index(check)
    assert text.index(check) < text.index("scripts/check_installed_wheel.py")


@pytest.mark.parametrize(
    "colliding_member",
    [
        "tf_build/source.py/",
        "tf_build/nested",
        "tf_build/nested/helper.py/",
        "tf_build-0.1.0rc1.dist-info/METADATA/",
        "tf_build-0.1.0rc1.dist-info",
    ],
)
@pytest.mark.parametrize("collision_first", [False, True])
def test_reject_ambiguous_file_directory_zip_layout_in_either_order(
    tmp_path: Path, colliding_member: str, collision_first: bool
) -> None:
    """Both *identically* malformed wheels must fail before payload comparison."""
    original = _wheel(tmp_path / "original.whl")
    candidate = tmp_path / "candidate.whl"
    with zipfile.ZipFile(original) as archive:
        members = [(item.filename, archive.read(item)) for item in archive.infolist()]
    collision = (colliding_member, b"" if colliding_member.endswith("/") else b"shadow")
    if collision_first:
        members.insert(0, collision)
    else:
        members.append(collision)
    for wheel in (original, candidate):
        with zipfile.ZipFile(wheel, "w") as archive:
            for name, contents in members:
                archive.writestr(name, contents)
    with pytest.raises(WheelPayloadMismatch, match="collid|ancestor|directory"):
        compare_wheel_payloads(original, candidate)


def test_explicit_and_implicit_directory_members_can_coexist(tmp_path: Path) -> None:
    """Legitimate wheels frequently spell directory entries out explicitly."""
    wheel = _wheel(tmp_path / "direct.whl")
    with zipfile.ZipFile(wheel, "a") as archive:
        for name in ("tf_build/", "tf_build/nested/", "tf_build-0.1.0rc1.dist-info/"):
            archive.writestr(name, b"")
    assert len(compare_wheel_payloads(wheel, wheel)) == 3
