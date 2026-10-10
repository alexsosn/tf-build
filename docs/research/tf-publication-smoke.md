# Research: composition of existing TF publication primitives

Issue: #26

## Source evidence

- tf-build `BuildWorkspace` requires an absent final target, creates a private sibling staging directory, and atomically publishes without clobbering on supported platforms. It cleans unpublished staging on exceptions, but deliberately does not certify its contents.
- tf-build `validate_tf_artifact` validates emitted `.tf` data by actual Text-Fabric `Fabric.explore/load` rather than the converter's own claims. `metadata` inspects header declarations; `all` explicitly reloads the complete node/edge inventory.
- tf-build `fingerprint_tree` binds the **raw shipped bytes** and names; derived Text-Fabric `.tf/` compiled caches are intentionally excluded. It is not a snapshot under concurrent mutation.
- tf-build `BuildReport` gives operational metrics/counts but is not a release certificate or artifact identity.
- CopticScriptorium-TF `copticscriptorium_tf/writer.py` writes a complete TF graph into a private directory using `Fabric.save` and only then publishes; Pseudepigrapha-TF `src/pseudepigrapha_tf/writer.py` likewise serializes using `Fabric.save`, with a different consumer-owned output tree layout.

## Missing gate

Individual primitives have real integration tests, but no **single executable consumer example** proves how to combine all of them without accidentally hashing compiled cache, overwriting published output, or claiming report-derived certification.

## Decision

Add a tiny self-contained **example script**, not a general-purpose runner: serialize a three-node TF graph with `Fabric.save` in `BuildWorkspace`, independently validate selected/all data, render operational report JSON as another shipped file, compute the byte fingerprint, publish once, and verify that post-publish bytes have the same identity. No external downloads, JSON/XML sidecars for corpus structure, or new core orchestration API.

The example has no corpus semantics other than a toy word-slot/sentence hierarchy. Integration tests call the example as a consumer of the **installed** package. A separate corruption regression uses a real typed TF feature and verifies that failed validation cleans staging, does not publish, and does not alter sibling artifacts.

## Boundaries

This proves internal composition and a real serializer/reload, not an Agora host sandbox smoke, not real historical manuscript conversion, and not cross-platform atomicity beyond `BuildWorkspace`'s documented capabilities.
