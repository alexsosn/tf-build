"""Feature documentation tests against real serialized Text-Fabric headers."""

from __future__ import annotations

from pathlib import Path

import pytest
from tf.fabric import Fabric  # type: ignore[import-untyped]

from tf_build.feature_docs import (
    FeatureReferenceError,
    render_feature_reference,
    scan_tf_feature_headers,
)


def _artifact(tmp_path: Path) -> Path:
    root = tmp_path / "core"
    root.mkdir(parents=True)
    tf = Fabric(locations=[str(root)], silent="deep")
    assert tf.save(
        nodeFeatures={
            "otype": {1: "word", 2: "word", 3: "sentence"},
            "text": {1: "Hello", 2: "world"},
            "label": {3: "S1"},
        },
        edgeFeatures={
            "oslots": {3: {1, 2}},
            "link": {3: {1}},
            "relation": {3: {1: "source"}},
        },
        metaData={
            "otype": {"valueType": "str"},
            "oslots": {"valueType": "str"},
            "text": {"valueType": "str", "description": "Surface token"},
            "label": {"valueType": "str"},
            "link": {"valueType": "str"},
            "relation": {"valueType": "str", "edgeValues": True},
            "otext": {
                "sectionTypes": "sentence",
                "sectionFeatures": "label",
                "fmt:text-orig-full": "{text} ",
            },
        },
        silent="deep",
    )
    return root


def test_header_scan_matches_real_node_edge_config_features(tmp_path: Path) -> None:
    directory = _artifact(tmp_path)
    features = scan_tf_feature_headers({"core": directory})
    by_name = {record.name: record for record in features}

    assert by_name["text"].kind == "node"
    assert by_name["text"].value_type == "str"
    assert by_name["relation"].kind == "edge"
    assert by_name["relation"].edge_values is True
    assert by_name["link"].edge_values is False
    assert by_name["otext"].kind == "config"
    assert by_name["otext"].value_type is None
    assert ("description", "Surface token") in by_name["text"].metadata
    assert tuple(sorted(by_name)) == tuple(sorted(record.name for record in features))


def test_scanner_reads_only_headers_not_bodies_or_cache(tmp_path: Path) -> None:
    directory = _artifact(tmp_path)
    source_file = directory / "text.tf"
    raw = source_file.read_bytes()
    metadata, sep, _body = raw.partition(b"\n\n")
    assert sep
    source_file.write_bytes(metadata + sep + b"CORRUPT BODY\n")
    before = {p.name: p.read_bytes() for p in directory.glob("*.tf") if p.is_file()}

    (directory / ".tf").mkdir()
    (directory / "scratch.tf").mkdir()
    records = scan_tf_feature_headers({"core": directory})

    assert "scratch" not in {r.name for r in records}
    assert ".tf" not in {r.name for r in records}
    assert before == {
        p.name: p.read_bytes() for p in directory.glob("*.tf") if p.is_file()
    }


def test_unknown_metadata_and_markers_preserved_and_rendered_safely(
    tmp_path: Path,
) -> None:
    directory = _artifact(tmp_path)
    (directory / "unusual.tf").write_text(
        "@node\n"
        "@valueType=str\n"
        "@arbitrary=<script>alert(1)</script> **bold** [link](http://example.org)\n"
        "@unknownMarker\n"
        "\n"
        "1\tcontent\n",
        encoding="utf-8",
    )
    records = scan_tf_feature_headers({"core": directory})
    unusual = next(record for record in records if record.name == "unusual")
    assert (
        "arbitrary",
        "<script>alert(1)</script> **bold** [link](http://example.org)",
    ) in unusual.metadata
    assert unusual.markers == ("unknownMarker",)

    pages = render_feature_reference(records)
    page = pages["core/unusual.md"]
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert r"\*\*bold\*\*" in page
    assert r"\[link\]" in page
    assert "unknownMarker" in page


@pytest.mark.parametrize(
    "data",
    [
        "@node\n@valueType=str\n1\tx\n",
        "@node\n@edge\n@valueType=str\n\n1\tx\n",
        "@node\n@valueType=str\n@valueType=int\n\n1\tx\n",
        "@node\n@valueType=str\n@edgeValues\n\n1\tx\n",
        "@whatever\n@valueType=str\n\n1\tx\n",
        "@node\n@valueType=decimal\n\n1\tx\n",
    ],
)
def test_malformed_regular_feature_header_fails(tmp_path: Path, data: str) -> None:
    directory = tmp_path / "core"
    directory.mkdir()
    (directory / "bad.tf").write_text(data, encoding="utf-8")
    with pytest.raises(FeatureReferenceError):
        scan_tf_feature_headers({"core": directory})



def test_missing_separator_cannot_scan_unbounded_header_text(
    tmp_path: Path,
) -> None:
    root = tmp_path / "core"
    root.mkdir()
    (root / "malformed.tf").write_text(
        "@node\n@valueType=str\n"
        + ("@extraKey=" + "x" * 1024 + "\n") * 512,
        encoding="utf-8",
    )
    with pytest.raises(FeatureReferenceError, match="header exceeds"):
        scan_tf_feature_headers({"core": root})


def test_symlink_feature_fails_but_suffix_matching_directory_ignored(
    tmp_path: Path,
) -> None:
    directory = _artifact(tmp_path)
    (directory / "not-a-feature.tf").mkdir()
    outside = tmp_path / "outside.tf"
    outside.write_text("@node\n@valueType=str\n\n1\tx\n", encoding="utf-8")
    (directory / "alias.tf").symlink_to(outside)

    with pytest.raises(FeatureReferenceError, match="symlink"):
        scan_tf_feature_headers({"core": directory})
    assert outside.is_file()


def test_two_modules_with_same_feature_name_keep_separate_pages(
    tmp_path: Path,
) -> None:
    core = _artifact(tmp_path)
    provenance = tmp_path / "provenance"
    provenance.mkdir()
    (provenance / "text.tf").write_bytes((core / "text.tf").read_bytes())

    first = scan_tf_feature_headers({"provenance": provenance, "core": core})
    second = scan_tf_feature_headers({"core": core, "provenance": provenance})
    assert first == second
    pages = render_feature_reference(first)
    assert "core/text.md" in pages
    assert "provenance/text.md" in pages
    assert pages == render_feature_reference(second)
    assert "core/text.md" in pages["index.md"]
    assert "provenance/text.md" in pages["index.md"]


def test_consumer_description_does_not_rewrite_shipped_metadata(
    tmp_path: Path,
) -> None:
    records = scan_tf_feature_headers({"core": _artifact(tmp_path)})
    pages = render_feature_reference(
        records,
        descriptions={("core", "text"): "Converter description"},
    )
    assert "Converter description" in pages["core/text.md"]
    assert "Surface token" in pages["core/text.md"]


@pytest.mark.parametrize("module", ["", ".", "..", "../bad", "bad/name", "x\\y"])
def test_unsafe_module_identifier_rejected(tmp_path: Path, module: str) -> None:
    with pytest.raises(FeatureReferenceError, match="module"):
        scan_tf_feature_headers({module: _artifact(tmp_path)})


def test_duplicate_renderer_records_rejected(tmp_path: Path) -> None:
    records = scan_tf_feature_headers({"core": _artifact(tmp_path)})
    with pytest.raises(FeatureReferenceError, match="duplicate"):
        render_feature_reference((*records, records[0]))
