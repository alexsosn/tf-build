# Research: sdist file ancestor collision validation (#74)

## Actual state
Main `dca00f32bdcd0d36aab2a7192b319a4f4f5aaf89`, post-merge CI https://github.com/alexsosn/tf-build/actions/runs/38143626564 passed all five jobs. In `scripts/wheel_manifest.py::_sdist_identity`, a tar.gz source archive is iterated without extracting, root and component syntax are checked, symlinks rejected, exact member names deduplicated, and `PKG-INFO` parsed with a 1 MiB bound. Its SHA256 is then included in wheel-manifest.json, consumed by `.github/workflows/ci.yml` and owner-approved `.github/workflows/release.yml`.

This checks each member in isolation, but not the consistency of its normalized filesystem **ancestry**. A member `tf_build-0.1.0rc1/pkg` with type regular-file and a member `tf_build-0.1.0rc1/pkg/mod.py` is accepted in either order, although a filesystem cannot simultaneously contain a regular file at `pkg` and children of that file. Similarly a regular root `tf_build-0.1.0rc1` plus nested mandatory `PKG-INFO` may be accepted. A hash manifest for such a structurally ambiguous archive is too permissive for release evidence. There is already analogous parent-file rejection for ZIP wheels in `scripts/compare_wheel_payloads.py::_package_payload`.

## Python tarfile fact-check
I wrote and reopened actual tar.gz files using stdlib `tarfile`. A directory header for `root/pkg/` appears as `root/pkg` upon iteration; thus an explicit regular `root/pkg` plus explicit directory `root/pkg/` **is already** handled by the existing `entries` check, contrary to an initial hypothesis. Explicit/implicit directory cohabitation is legitimate and must continue to work. The missing guard is specifically an implicit ancestor that was never a tar member name.

## Proposed boundary
Maintain separate sets of normalized regular-file paths and implicit or explicit directory paths. For each tar member, forbid regular files at paths previously inferred as directories, forbid any path below a known regular file, and infer directory parents of all encountered paths regardless of order. Allow an explicit directory member at a previously implicit directory. Preserve existing rejection of duplicate explicit archive entries. Do not change wheel parity, published package APIs, corpus data or release-tag controls.

## Security, backward compatibility and tests
Fail closed for ambiguous sdist paths without extracting/execing arbitrary members. No change for setuptools/build generated sdists with normal root directory headers or sparse explicit directory records. RED-first parametrized tar.gz tests should demonstrate file ancestors in both orders and root-as-file; a positive test should prove the explicit directory/implicit directory case. Real CI distribution jobs must remain green to establish that generated sdists conform.
