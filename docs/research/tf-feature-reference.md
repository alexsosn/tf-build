# Research: artifact-derived Text-Fabric feature reference

Issue: #9

## Consumer/code evidence

- TLHdig-TF `programs/tlhdig/featuredocs.py` reads only feature-file headers up to the first blank line; its generated pages contain kind, valued-edge marker, description, module identity and stable metadata. The shipped artifact—not a converter plan—is the inventory authority. It verifies scholarly descriptions against TLHdig-owned `featuremeta.DESCRIPTIONS`.
- TLHdig-TF #110 recorded a concrete regression: `Path.glob("*.tf")` returns Text-Fabric's compiled-cache directory named `.tf/` and arbitrary other suffix-matching directories, not only feature files. These directories must be ignored while a `*.tf` symlink must fail closed. tf-build #19 reproduced the analogous issue with a real `Fabric.load()` cache.
- Pseudepigrapha-TF's `feature_docs.py` describes the converter's **supported** schema, including features absent from the emitted corpus, scholarly direction/cardinality, and controlled vocabularies from local graph/semantic contracts. Those cannot be inferred from emitted file headers. They remain converter-owned.
- Text-Fabric 13.1 `Fabric.explore()` parses feature metadata without reading full payloads; however TLHdig's proven header-only parser avoids building TF APIs and is adequate for pure documentation. `Fabric.loadAll()` can be expensive at scale and is unnecessary here.

## Extraction decision

Provide a small **artifact-header inventory** and **pure Markdown render** API. Namespaced `module/feature` records support multiple TF modules without silently overwriting identically named features; the caller can label a module as optional in higher-level docs. Only actual regular `*.tf` files are reported.

Each immutable record contains module, filename stem, kind (node/edge/config), `valueType` (if any), whether `@edgeValues` appears, and all remaining header metadata and unknown standalone markers. No corpus interpretation or artificial description for missing `@description` is generated.

A pure rendering function can accept optional caller-supplied plain-text descriptions indexed by `(module, name)`. The published header's own `@description`, if present, remains visible among metadata, so a caller cannot silently rewrite published metadata. Rendering yields a deterministic, namespaced `index.md` plus one per-feature Markdown page.

## Safety and determinism

- Fail on symlink candidate files, nonregular `*.tf` objects and malformed/ambiguous headers; ignore directories, including `.tf/`.
- Read only until the first empty line, never the payload. Reject a missing blank separator to avoid silently treating body as metadata.
- Reject conflicting primary markers and duplicate metadata keys. Preserve unknown keys and extra standalone markers instead of dropping them.
- Escape caller/header prose as **text**, not executable HTML or uncontrolled Markdown links; no network fetches or body data loads.
- Sort modules and feature names independent of directory creation/traversal order. Require safe module and filename identifiers because they become output page paths.
- Outputs are computed in memory. Write/check/update policies belong to consumers; do not add a destructive on-disk docs synchronizer now.

## Non-goals

- replacing TF validation #6 or certification of feature bodies;
- corpus-supplied semantic contracts or supported-but-unemitted features;
- app-specific feature page path conventions;
- enforcing cross-module uniqueness (overlays can legitimately repeat feature names);
- inferring node-type applicability, edge cardinality, or source/target semantics from header-only data.
