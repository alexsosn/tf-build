# Issue #96 — Agora receipt is a reserved root file, not an output subtree

## Real host evidence
- Current tf-build `src/tf_build/agora.py::_relative_path` compares the **full** relative path to `agora-materialization.json`, so `agora-materialization.json/payload.tf` is accepted as a generated path.
- The current Agora host `alexsosn/Agora/scripts/agora_materialize.py` invokes `_write_provenance(staging.output / "agora-materialization.json", provenance)` (near line 1379). Its `_write_provenance` (around lines 1198–1218) opens the target as a new regular file with `O_CREAT | O_EXCL`. Existing directory or file at that root name blocks receipt creation.
- `agora_output_path` promises path preflight without creating files and protects the host-reserved root receipt. A materializer treating that receipt filename as an output directory can fail *after* performing conversion. It should fail on path request before writing anything.

## Correct boundary
Disallow the reserved filename **only as the first path segment**, so `agora-materialization.json` and `agora-materialization.json/nested` are rejected. Do not ban `tf/agora-materialization.json` or `other-agora-materialization.json`, which do not collide with the host's root receipt. Do not add filesystem operations or mutable configuration.

## Verification and limitations
Use a real temporary root, prove no path or directory is created, retain existing tests for symlinks/portable paths, and examine the final real host receipt writer independently. No full Agora live materialization or external dataset download is needed for this narrow path preflight change. This does not change publication, producer policy, or release #60.
