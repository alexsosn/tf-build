# Research: stale binary caches can mask corrupt raw TF sources

Issue #33

## Verified upstream behavior

`annotation/text-fabric/tf/core/data.py::Data.load` compares `origTime = _getModified()` with `binTime = _getModified(bin=True)`. When `binTime >= origTime`, the non-metadata path calls `_readTf(metaOnly=True)`, then `_readDataBin`. The raw feature **body** is not parsed in that branch. Text-Fabric's `clearCache()` deletes compiled files in the original module tree, which would violate our source-preserving read-only validation intent.

Our `validate_tf_artifact(level="all")` calls `Fabric.load` on the caller's artifact directory. A stale `.tf/<PACK_VERSION>/*.tfx` cache can thus mask a corrupt same-mtime raw `count.tf` body. This is a false-positive release gate: fingerprints intentionally exclude these caches and bind raw bytes.

## Options considered

- Calling `clearCache()` directly: **reject**; deletes caller-owned cache and produces side effects.
- Touching source file mtimes: **reject**; mutates artifact state, hides original provenance, and can trigger rebuilds.
- Replacing Text-Fabric's internal `Data.binDir/binPath` private fields: **reject**; fragile against upstream internals.
- Loading from a temporary source-only view: **choose**. Link real `*.tf` files into a private temporary directory (zero-copy when supported on same filesystem); fall back to copying bytes if hardlinking is unavailable. The view contains no `.tf/` cache. Text-Fabric is then forced to parse the raw feature bodies, and generated caches exist only under that temporary view, which is deleted on exit.

## Semantics

`metadata` remains a header-only check in the caller tree. `selected` and `all` use an isolated clean source view, so their explicit load depth refers to actual emitted `.tf` data, not an existing compiled pickle. Preserve selected-vs-all feature selection, no-clobber and requirement checks.

Hardlinks are read-only to this consumer (Text-Fabric `Fabric.load` parses sources and writes only derived `.tf/` caches). As with the existing validator and fingerprint API, there is no atomic snapshot guarantee against concurrent **in-place** source-file modification. A private view prevents stale compiled cache reuse, not every race.

Fallback copying can double I/O/disk use for very large corpora or cross-filesystem temp roots; benchmark if actual consumers show performance regressions. Prefer temp sibling directory on the same filesystem when writable. If safe staging cannot be created, fail clearly rather than silently trusting caches.

## Evidence quality

The regression test must reproduce the risk using a real `Fabric.save` fixture and compiled `.tfx` cache. After corrupting only the raw body, restore original `os.utime(ns=...)` so `binTime >= origTime`; confirm a fresh source parse fails. No mocking of TF's loader or fake binary cache.
