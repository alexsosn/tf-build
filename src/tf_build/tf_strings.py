"""Fail-closed string preflight for Text-Fabric's raw CR serialization gap.

Current Text-Fabric escapes LF, TAB and backslash in string feature bodies,
but writes literal CR verbatim. Universal-newline reading can then shift
values to the wrong nodes. No source text is ever rewritten by this module.
"""

from __future__ import annotations

from collections.abc import AbstractSet, Mapping


class TFStringSafetyError(ValueError):
    """A string cannot be serialized by Text-Fabric without possible data loss."""


def require_tf_safe_string(
    value: str,
    *,
    feature: str,
    node: int,
    target: int | None = None,
) -> str:
    """Return original text or reject literal U+000D with attribution.

    Call this before CV.walk or direct feature emission. Converters needing
    carriage returns should encode them losslessly in their own TF model
    before invoking this check; no normalization is performed here.
    """
    if "\r" in value:
        location = f"node {node}" if target is None else f"edge {node} -> {target}"
        raise TFStringSafetyError(
            f"Text-Fabric feature {feature!r} {location} contains unsafe U+000D"
        )
    return value


def preflight_tf_save_values(
    node_features: Mapping[str, Mapping[int, object]],
    edge_features: Mapping[
        str, Mapping[int, Mapping[int, object] | AbstractSet[int]]
    ],
) -> None:
    """Check all string values in standard Fabric.save feature mappings.

    Does not validate feature type metadata or edge-set graph semantics:
    those remain Text-Fabric's responsibility. Integer/None node values and
    unvalued edge sets do not contain a string to check.
    """
    for feature, values in node_features.items():
        for node, value in values.items():
            if isinstance(value, str):
                require_tf_safe_string(value, feature=feature, node=node)

    for feature, nodes in edge_features.items():
        for node, targets in nodes.items():
            if isinstance(targets, Mapping):
                for target, value in targets.items():
                    if isinstance(value, str):
                        require_tf_safe_string(
                            value, feature=feature, node=node, target=target
                        )


__all__ = [
    "TFStringSafetyError",
    "preflight_tf_save_values",
    "require_tf_safe_string",
]
