# ADR 0001 — Defer a universal Text-Fabric graph/writer abstraction

**Status:** Accepted (research-only; no generic `TFGraph` implementation)  
**Issue:** [#10](https://github.com/alexsosn/tf-build/issues/10)  
**Date:** 2026-10-10

## Problem

Several converters build a Text-Fabric graph, but their models and serializers are not interchangeable. Extracting a universal graph too early could force a false common ontology, transform ordered events into artificial spans, or duplicate interfaces already provided by Text-Fabric.

## Grounded comparison

### CopticScriptorium-TF — writer-independent word graph

`copticscriptorium_tf/_graph_core.py` declares immutable `GraphSlot`, `GraphNode`, and `GraphEdge` models. Slots are **words**. Nodes store sorted disjoint `slot_ranges`, document/source provenance, source-word ordinals, occasional character-layout anchors and cross-document relations. `copticscriptorium_tf/writer.py` projects the graph to batches of `Fabric.save(nodeFeatures=..., edgeFeatures=..., metaData=...)` and publishes a fresh destination without clobbering.

### Pseudepigrapha-TF — serializable feature dictionaries

`src/pseudepigrapha_tf/graph.py` exposes `TFData` with `node_features`, `edge_features` and `metadata`, and a keyed `_Builder` specialized to textual versions, variants and apparatus. `src/pseudepigrapha_tf/writer.py` adds text-format dependencies and writes through `Fabric.save`. Its core data shape is already close to the Text-Fabric serialization boundary, unlike Coptic's richer, immutable intermediate IR.

### TLHdig-TF — streamed sign-slot conversion

`programs/tlhdig/convert.py` walks manuscript source events with a mutable director/`_State` and calls `CV.walk` to emit **sign** slots, layout layers and source-preservation checks. Introducing a mandatory materialized cross-corpus graph would either duplicate the walker event semantics or require an expensive general event intermediate form.

### Native Text-Fabric contracts

`annotation/text-fabric/tf/core/fabric.py` supports `Fabric.save` feature dictionaries. `annotation/text-fabric/tf/convert/walker.py` supports an event director, `CV.slot`, `CV.node`, `CV.link`, `CV.edge`, and reorders keyed slots when appropriate. A proposed common writer must preserve both rather than selecting just one.

## Decision

**Do not publish a shared `TFGraph`, universal slot schema, or writer interface in the first tf-build API.** None of the observed models provides a stable semantics-free abstraction that is materially simpler than its existing Text-Fabric boundary.

Continue extracting verifiable cross-project operations: immutable acquisition and source revision, safe create-only staging, raw artifact identity, operational reports, metadata/selected/all artifact loading, and artifact-derived documentation. These do not impose corpus interpretation.

## Conditions to revisit

A narrower library component may be considered only after two actual consumers demonstrate matching semantics and duplication, with tests covering **both a word-slot and sign-slot** corpus. Candidate: normalized sorted positive non-contiguous slot intervals, provided this does not force span contiguity or representation of events as intervals. Measure runtime memory and serialization cost against existing TF idioms. Do not infer edge direction/cardinality, section semantics, node-type ontology or provenance meaning from generic feature names.

## Consequences

No breaking abstraction for current converters. More corpus-owned graph code is acceptable until repeated mechanics justify extraction. Future universal-graph proposals require their own research, plan and TDD ticket with real data from at least two conversion strategies.
