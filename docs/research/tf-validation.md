# Research: Text-Fabric artifact clean-reload validation

Issue: #6

## Scope

Validate a generated Text-Fabric corpus artifact independently of the consumer parser or writer-specific IR. The shared layer must detect broken/missing TF files, incompatible feature metadata, unloadable format dependencies, and optional exhaustive-load failures without embedding corpus semantics.

## Consumer evidence

### CopticScriptorium-TF

The writer already stages a complete artifact, validates its writer-independent graph, requires `otype.tf`, `oslots.tf`, and `otext.tf`, and only then publishes. It does not currently perform a fresh Text-Fabric reload after serialization.

### TLHdig-TF

The converter can perform a fresh `Fabric(...).loadAll()`, but current project documentation records that exhaustive loading of a large artifact can be very expensive. Its ordinary validators therefore often load only the features needed by a gate. A malformed text format that references a missing feature can make Text-Fabric loading fail, so a fresh runtime load is a meaningful artifact-level check.

### Text-Fabric 13.1

Relevant supported behavior:

- `Fabric.features` is documented as the catalogue of discovered features and their metadata, whether loaded or not.
- `Fabric.explore()` metadata-loads all discovered features and classifies node/edge/config/computed features without loading every feature body.
- `Fabric.load(features)` always loads warp/config dependencies plus explicitly requested features and builds a fresh API.
- `Api.isLoaded(pretty=False)` reports loaded feature kind, value type, edge-value status, metadata and source.
- `Fabric.loadAll()` attempts to load every loadable node/edge feature, but its 13.1 implementation discards the boolean result of the final `load(..., add=True)` call and returns the API created before that add-load. Its return value alone is therefore not a reliable exhaustive-success signal.
- `T.formats`, `T.sectionTypes`, and `T.sectionFeatures` expose the compiled text/section configuration after a successful load.

## Validation levels

Expose two public runtime modes:

1. **selective** (default): inspect all feature metadata, then fresh-load warp/config dependencies plus caller-required features. This is the normal build gate.
2. **exhaustive**: fresh warp/config load followed by an explicit checked `load(all_discovered_features, add=True)`, so every loadable node and edge feature must parse/compile successfully. Do not use `loadAll()` as the success oracle because it ignores that add-load result in TF 13.1.

Metadata inspection is always performed internally; it is not a separate public success mode because this ticket's purpose includes a clean runtime reload.

The result must record which mode actually ran so selective validation cannot be mistaken for exhaustive validation.

## Declarative contract

The shared contract may describe:

- required node/edge feature names;
- optional expected value type (`str` or `int`);
- optional expected `edgeValues` flag for edge features;
- required text-format names;
- optional exact section type/feature tuples.

These are caller-supplied structural expectations, not corpus semantics. The shared package must not know that a particular corpus has a `lemma`, `line`, `document`, etc.

`otype.tf` and `oslots.tf` are mandatory for a corpus artifact. `otext.tf` is required only when text-format or section expectations are declared; Text-Fabric itself permits feature-only datasets without it.

## Format and section checks

A fresh `Fabric.load()` compiles the text API and loads format/section dependencies declared by `otext`. Therefore:

- a required format is usable at the shared structural level if the fresh load succeeds and its name is present in `api.T.formats`;
- section expectations are checked against `api.T.sectionTypes` and `api.T.sectionFeatures` after the same successful load.

The shared validator does not assert corpus-specific rendered strings or scholarly section labels. Consumer projects remain responsible for semantic smoke tests.

## Derived cache side effects

Text-Fabric has no supported no-cache runtime-load switch. Ordinary feature loading may write compiled `.tfx` data under the artifact's derived `.tf/` cache directory.

The shared validator must not leave those platform/version-specific bytes in a freshly staged artifact. It should clear Text-Fabric's compiled cache after runtime validation in a `finally` path, on both success and failure. This cleanup may remove/rebuild derived cache from an already-published dataset, but substantive `*.tf` feature/config files must remain byte-identical.

This matches the artifact-fingerprint boundary researched for #7: compiled `.tf/` cache is derived and non-shipping.

## Failure semantics

- reject a symlinked/non-directory artifact root;
- reject missing/symlinked/non-regular mandatory or required feature files;
- fail on missing required feature, kind mismatch, value-type mismatch, or edge-values mismatch;
- fail when fresh selective/exhaustive Text-Fabric load fails;
- fail when a required text format or expected section tuple is absent;
- preserve the primary validation error if cache cleanup also fails, and attach cleanup failure as an exception note;
- if cleanup alone fails after otherwise successful validation, report validation failure because the no-cache postcondition was not restored.

Hostile concurrent filesystem replacement is outside this contract, consistent with the current BuildWorkspace boundary.

## Non-goals

- corpus-semantic assertions;
- browser/app configuration validation;
- Context-Fabric behavior;
- provenance/add-on module composition;
- artifact hashing/fingerprinting (#7);
- publication/replacement semantics;
- suppressing Text-Fabric's own validation rules.
