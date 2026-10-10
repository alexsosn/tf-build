"""Real TF CR-misattribution oracle and preflight regression tests."""

from __future__ import annotations

from collections.abc import Mapping, Set
from copy import deepcopy
from pathlib import Path

import pytest
from tf.fabric import Fabric  # type: ignore[import-untyped]

from tf_build.tf_strings import (
    TFStringSafetyError,
    preflight_tf_save_values,
    require_tf_safe_string,
)


def test_real_text_fabric_loses_node_identity_from_literal_cr(
    tmp_path: Path,
) -> None:
    """Independent upstream oracle, not a mock of tf-build's preflight."""
    root = tmp_path / "tf"
    root.mkdir()
    node_features = {
        "otype": {1: "word", 2: "word", 3: "word", 4: "sentence"},
        "text": {1: "alpha\rspill", 2: "beta", 3: "gamma"},
        "label": {4: "S1"},
    }
    edge_features = {"oslots": {4: {1, 2, 3}}}
    saved = Fabric(locations=[str(root)], silent="deep").save(
        nodeFeatures=node_features,
        edgeFeatures=edge_features,
        metaData={
            "otype": {"valueType": "str"},
            "oslots": {"valueType": "str"},
            "text": {"valueType": "str"},
            "label": {"valueType": "str"},
            "otext": {
                "sectionTypes": "sentence",
                "sectionFeatures": "label",
                "fmt:text-orig-full": "{text} ",
            },
        },
        silent="deep",
    )
    assert saved
    assert b"\r" in (root / "text.tf").read_bytes()

    api = Fabric(locations=[str(root)], silent="deep").load(
        "text", silent="deep"
    )
    assert api
    assert api.F.text.v(2) != node_features["text"][2]


def test_scalar_preflight_rejects_cr_without_echoing_sensitive_text() -> None:
    source = "secret value\rcontinuation"
    with pytest.raises(TFStringSafetyError) as caught:
        require_tf_safe_string(source, feature="bibliography", node=123)
    message = str(caught.value)
    assert "bibliography" in message
    assert "123" in message
    assert "U+000D" in message
    assert "secret" not in message
    assert "continuation" not in message


def test_valued_edge_preflight_identifies_both_nodes() -> None:
    with pytest.raises(TFStringSafetyError) as caught:
        require_tf_safe_string(
            "secret edge\rcontinuation",
            feature="relation",
            node=12,
            target=49,
        )
    message = str(caught.value)
    assert "relation" in message
    assert "12" in message
    assert "49" in message
    assert "secret" not in message


@pytest.mark.parametrize(
    "value",
    ["", "hello", "line\nfeed", "tab\tseparator", "slash\\test", "𐎀 𐎁", "x\v y"],
)
def test_scalar_preflight_preserves_supported_strings_exactly(value: str) -> None:
    assert require_tf_safe_string(value, feature="text", node=1) == value


def test_aggregate_preflight_inspects_node_and_valued_edge_without_mutation() -> None:
    word_text = {1: "alpha\nbeta", 2: "gamma"}
    valued_edges = {3: {1: "edge\tvalue", 2: "other"}}
    nodes: Mapping[str, Mapping[int, object]] = {
        "otype": {1: "word", 2: "word", 3: "sentence"},
        "text": word_text,
        "count": {1: 7, 2: None},
    }
    edges: Mapping[str, Mapping[int, Mapping[int, object] | Set[int]]] = {
        "oslots": {3: {1, 2}},
        "link": valued_edges,
    }
    before_nodes = deepcopy(nodes)
    before_edges = deepcopy(edges)
    preflight_tf_save_values(nodes, edges)
    assert nodes == before_nodes
    assert edges == before_edges

    word_text[2] = "private\rnewline"
    with pytest.raises(TFStringSafetyError, match="text") as caught:
        preflight_tf_save_values(nodes, edges)
    assert "private" not in str(caught.value)
    word_text[2] = "gamma"

    valued_edges[3][2] = "edge\rPRIVATE_SENTINEL_EDGE"
    with pytest.raises(TFStringSafetyError) as caught:
        preflight_tf_save_values(nodes, edges)
    assert "link" in str(caught.value)
    assert "3" in str(caught.value)
    assert "2" in str(caught.value)
    assert "PRIVATE_SENTINEL_EDGE" not in str(caught.value)
