# Initial development plan

The bootstrap issue establishes the repository contract. Subsequent behavior is intentionally split into focused issues so every change can follow research → plan → RED → implementation → exact-head verification → independent adversarial review.

## Wave 0 — bootstrap

- package metadata and importable `tf_build` namespace;
- authoritative agent instructions and autonomous loop;
- pytest, Ruff and strict mypy configuration;
- CI on the supported Python matrix;
- architecture/research documents;
- initial issue backlog.

## Wave 1 — source and workspace primitives

1. immutable Git source identity and local verification;
2. staged/pinned Git acquisition;
3. safe build workspace and atomic publication.

These should be validated first against ORAEC-TF and CopticScriptorium-TF requirements.

## Wave 2 — artifacts and reports

4. structured build/provenance report;
5. TF clean-reload and required-feature validation;
6. deterministic artifact manifest/fingerprint;
7. stale-output/replacement-semantics checks.

## Wave 3 — adapters and generated references

8. Agora materializer workspace/report helpers;
9. generated TF feature documentation helpers.

## Deferred research

- generic writer-independent `TFGraph`;
- serializer abstraction over `CV.walk` versus `Fabric.save`;
- archive/Zenodo acquisition helpers;
- Text-Fabric-Factory integration protocol.

These need cross-project evidence before API design.

## Bootstrap acceptance

The bootstrap PR may contain no corpus semantics. It is complete when the repository can be installed and quality-checked, the workflow is explicit, and a real prioritized backlog exists.
