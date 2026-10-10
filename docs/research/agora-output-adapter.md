# Research: minimal Agora materializer output primitives

Issue: #8

## Sources inspected

- `alexsosn/Agora/scripts/agora_materialize.py` and current schema `registry/schema/materializer-plugin.schema.json`
- `alexsosn/Agora/tests/test_materialization_sandbox_workspace.py`
- `alexsosn/CopticScriptorium-TF/copticscriptorium_tf/agora.py`, `agora.materializer.json`
- `alexsosn/Pseudepigrapha-TF/agora.materializer.json`, `src/pseudepigrapha_tf/cli.py`
- tf-build source snapshot, build workspace and operational report modules

## Evidence

Agora owns network acquisition, explicit trust/installed environment, sandbox enforcement, source provenance, a private existing empty `{output}` directory, required-output-path validation, its reserved `agora-materialization.json` receipt and final atomic publication. A plugin's job is only to perform its offline corpus-specific conversion into the host-provided output root.

Agora binds `{source_revision}` to the resolved Git commit for git acquisition but passes an empty string for user-local/archive sources. That empty string is **not** a Git commit and must not be converted into an invented full SHA. Coptic explicitly introduces the consumer-local `unversioned-local` sentinel; Pseudepigrapha passes a possibly absent commit through to its existing converter. These policies must stay local.

Output layouts also genuinely differ: Coptic writes `tf/otype.tf`, `tf/oslots.tf`, `conversion-summary.json` at root; Pseudepigrapha writes `otype.tf`, `oslots.tf`, `conversion-report.json` at root.

Agora validates output paths, and its host receipt `agora-materialization.json` is reserved. A plugin must not write that receipt, take over host staging, re-acquire source data or publish the host's final destination. No library helper can enforce network denial by itself; that requires Agora's sandbox.

## Extraction

Only these isolated mechanics justify a small shared API now:

1. Validate the host-provided existing, empty, non-symlink output root without creating or modifying it.
2. Accept an optional full 40/64-hex immutable Git `source_revision`, returning `None` on the host's empty string; reject symbolic/ambiguous non-empty values.
3. Validate safe, portable, relative POSIX paths for generated artifacts (without taking over layout); refuse the reserved host receipt.
4. Produce a path within the private output root without performing publication.

No `AgoraMaterializer` superclass, automatic conversion wrapper, sandbox implementation, manifest parser or runtime Agora dependency. Normal `BuildWorkspace` is for a caller who owns publication of a **nonexistent final destination**, whereas Agora already provides and owns the private output directory: they have different lifecycles and should not be conflated.

## Integration evidence and limitations

The tests should use the exact structural behavior of both Coptic and Pseudepigrapha adapter layouts, but this Python library does not vendor Agora or import its host code at runtime. A full Agora sandbox workflow remains a consuming-project integration gate.

## Security boundary

All checks are preflight in a private host-owned directory. If other processes mutate it concurrently, path checks are not an atomic authorization guarantee. The Agora sandbox/host is the isolation boundary.
