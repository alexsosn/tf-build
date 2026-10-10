# Research: Text-Fabric raw carriage returns corrupt feature attribution

Issue: #37

## Real corpus evidence

ORAEC-TF issue #40 and its independent pinned-source audit report an actual corpus defect: oraec6.bibliography contains 19 literal U+000D carriage returns, and a later raw oraec10.bibliography value appeared under oraec29 (+19 nodes). A full graph load and node-count checks passed (ORAEC GitHub Actions 38062529497). Its project-local lossless feature codec is separate work.

## Upstream serializer evidence

Verified annotation/text-fabric/tf/core/helpers.py function tfFromValue: it escapes backslash, U+0009 (TAB) and U+000A (LF), but not U+000D (CR). The inverse valueFromTf has no CR decoding. The Text-Fabric Data._writeDataTf function uses tfFromValue for both node and valued edge feature bodies. Data._readDataTf consumes physical lines via universal-newline text reading and uses implicit increasing node IDs if a row has no node specifier. Literal CR can introduce an extra physical row or be collapsed with LF, corrupting feature value-node mapping. A correct regression must compare feature, node and exact source value, not merely node counts.

## Extraction boundary

tf-build must not duplicate Text-Fabric serialization or ORAEC corpus-specific source-location preservation. Two narrow generic preflights are justified:

- require_tf_safe_string(value, *, feature, node, target=None) for CV.walk and per-value emission, returning original str unchanged on success and raising TFStringSafetyError (without exposing raw text) on U+000D.
- preflight_tf_save_values(node_features, edge_features) for the ordinary Fabric.save node/edge feature dictionaries, scanning both node strings and valued-edge strings; skipping ints, None and unvalued edges.

Only U+000D is rejected based on proven physical-line corruption. Text-Fabric already escapes LF and TAB. There is insufficient evidence that other control characters cause this specific failure; do not silently normalize source data. Consumers needing literal CR must implement project-owned lossless encoding before preflight.

## Performance and limitations

The scan costs linear time over the values and performs no I/O or mutation. It must run before Fabric.save or CV.walk; it cannot repair already emitted TF files. This is not proof of scholarly roundtrip semantics or an automatic patch to upstream TF. Revisit this gate after an upstream CR-safe serialization release with actual parity tests.
