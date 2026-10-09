# Research: Text-Fabric artifact validation

Issue: #6

## Consumer evidence

- CopticScriptorium-TF `copticscriptorium_tf/writer.py` validates its internal graph, creates a fresh sibling staging directory, writes TF using `Fabric.save`, checks `otype.tf`, `oslots.tf` and `otext.tf`, and atomically publishes. This is a valuable filesystem gate but does not independently reload the written dataset.
- TLHdig-TF `programs/tlhdig/convert.py` uses `Fabric(...).loadAll()` as an optional post-conversion check. It documents that this can compile about 106 features and cost ~35 minutes on the full corpus; `load=False` is used when later compaction would invalidate the cache.
- TLHdig-TF `programs/validate_current.py` also carries extensive corpus-meaning gates (repair, morphology, round-trip, structure, manuscripts, alignment, app, census). These remain project-owned; tf-build must not interpret them.
- ORACC-TF was searched for `loadAll`/shared writer validations, but no matching reusable loader primitive was established from the retrieved code. This is not evidence to invent ORACC-specific contracts.

## Text-Fabric 13.1 behavior inspected

- `Fabric.explore()` invokes feature metadata loading and returns node, edge, config and computed feature sets without loading every data payload.
- After metadata load, `Fabric.features[name]` exposes `dataType`, `isEdge`, `isConfig`, `edgeValues`, `metaData`, and an error indicator.
- `Fabric.load(features)` independently loads warp features, optional `otext`, declared section/text dependencies, and requested features; it returns an API or `False`.
- `Fabric.loadAll()` calls `load("")` followed by `explore()` and `load(all_node_and_edge_features, add=True)`, but discards the boolean result of that second load. Therefore the shared exhaustive gate should explicitly check the second load result instead of trusting the `loadAll()` return alone.
- `otext.tf` is optional in the upstream TF loader; consumers that require a text configuration should explicitly opt in to its presence.

## Design conclusion

Expose one validation function with explicit validation levels:

1. **metadata**: filesystem preflight and Text-Fabric metadata enumeration with required feature kind/value-type/edge-value checks; no claim about feature-data readability.
2. **selected** (default): metadata checks plus a fresh independent `Fabric.load(...)` of warp and explicitly required features; Text-Fabric may load extra format/section dependencies.
3. **all**: selected checks plus an explicit `load(..., add=True)` of every discovered node/edge feature, checking its return value.

The result records the level actually performed. A metadata-only pass must never be described as a successfully reloaded corpus.

Required features are caller-supplied structural expectations: name, node/edge/config kind, `str`/`int` value type, and valued/unvalued edge flag. No corpus-specific feature names or node/slot types are built in.

Fail closed on absent directory, unsafe symlinked TF feature files, missing warp files, absent required features, metadata conflicts, and failed requested load. Ignore Text-Fabric's generated `.tf/` compiled cache; artifact fingerprinting is separate issue #7.

## Test strategy

Tests must use actual Text-Fabric 13.1 `Fabric.save` to produce small TF datasets, and actual fresh `Fabric.load` for validation. Include ordinary node/edge/config feature contracts; missing/invalid metadata; load failure after corrupting a feature body; level differentiation; and symlink/path adversarial cases. No mocked `Fabric` for the principal correctness evidence.

## Non-goals

- corpus schema, ontology or scholarly interpretation;
- proving that every TF query works;
- artifact hashing/release certification;
- enforcing an `otext` configuration on module-only artifacts;
- forcing costly exhaustive loading at every build;
- treating a successful metadata scan as proof that the TF feature bodies are usable.
