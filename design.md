# tf-build design

## Purpose

`tf-build` supplies reusable infrastructure for reproducible Text-Fabric corpus materializers.

It deliberately does not decide what a corpus means. A consuming project owns parsing, canonical source modelling, scholarly semantics and the TF ontology. tf-build owns reusable mechanics around those decisions.

## Layer boundary

```text
upstream source
    |
    |  project-specific acquisition policy may delegate to tf-build
    v
verified local SourceSnapshot          <- tf-build
    |
    v
project parser / canonical IR          <- corpus project
    |
    v
project TF graph/director/schema       <- corpus project
    |
    v
Text-Fabric CV.walk/Fabric.save        <- Text-Fabric
    |
    v
staged TF artifact                     <- tf-build workspace
    |
    +--> validation / fingerprint       <- tf-build
    +--> build report / provenance      <- tf-build
    |
    v
published artifact / Agora handoff     <- tf-build helpers + host
```

## Design principles

1. **Composition over inheritance.** No mandatory `BaseConverter` class.
2. **Fail closed at infrastructure boundaries.** Ambiguous revisions, unsafe paths, dirty snapshots, stale outputs and failed reloads are errors unless a caller opts into a separately documented mode.
3. **Offline conversion.** Acquisition may use the network; conversion/build code receives local materialized input.
4. **Immutable evidence.** Reproducible claims bind to immutable source identity and generated artifact identity.
5. **No scholarly semantics in core.** Generic helpers may carry opaque metadata but may not reinterpret source data.
6. **Do not duplicate upstream TF/TFF.** Use Text-Fabric graph validation/serialization and Text-Fabric-Factory XML/TEI facilities where appropriate.
7. **Deterministic, machine-readable contracts.** Stable dataclasses/JSON reports first; convenience CLIs are thin adapters.
8. **Consumer-driven extraction.** A proposed abstraction needs evidence from at least two consumers unless it is an isolated infrastructure primitive with an obvious generic contract.

## Planned modules

The names below are provisional API areas, not a commitment to implement all of them immediately:

- `tf_build.source` — source identity and acquisition.
- `tf_build.workspace` — safe staging and publication.
- `tf_build.report` — build result/provenance records.
- `tf_build.validate` — TF artifact validation and clean reload.
- `tf_build.fingerprint` — deterministic artifact manifests/hashes.
- `tf_build.docs` — feature-reference generation.
- `tf_build.agora` — host adapter primitives.
- optional future `tf_build.graph` / `tf_build.writer` only after cross-project evidence.

## Compatibility target

Initial package support targets Python 3.11+ and Text-Fabric 13.x. The exact dependency range is part of the package metadata and CI contract and may be widened only with tests.
