# Research: control characters violate portable report paths

Issue: #47

## Observed implementation

`src/tf_build/report.py::_validate_artifact_path` checks that `ArtifactSummary.path` is a nonempty relative POSIX-style identifier, with no `/` root, drive prefix, `\\`, dot traversal or empty components. It does not check ASCII control characters.

Hence `ArtifactSummary("tf/\\x00metadata", 1, 1)` is constructible despite the NUL being illegal in filesystem paths on the supported platforms. `BuildReport.to_json()` uses `json.dumps`, which escapes these characters, making the error hard to notice in JSON while preserving an invalid artifact reference for consumers. CR/LF/TAB/DEL are also inappropriate for a **portable** logical identifier even though certain POSIX filesystems may permit non-NUL controls.

The Git provenance validator already rejects C0 and DEL and `tf_build.agora` and `tf_build.fingerprint` guard NUL in path-like inputs. Similarity does not justify a general shared path-abstraction: the report path is a distinct typed contract.

## Decision

Reject ASCII C0 controls (`ord(ch) < 32`) and DEL (`ord(ch) == 127`) in the existing report path helper, without changing valid Unicode/POSIX punctuation, existing relative path rules or metric/artifact semantics. Report errors must not echo caller-supplied path bytes.

This is a *portable report identifier* policy, not a universal validator for any possible POSIX filename or a new conversion/Agora policy.
