# Research: durable release readiness for tf-build 0.1.0rc1

Issue #60; ORAEC-TF consumer issue #59; parent tf-build #53.

## Verified mainline on 2026-10-11

Main `pyproject.toml` still reports `tf-build==0.1.0.dev0`. GitHub Releases API for `alexsosn/tf-build` returns `[]`. Merged PR #59 adds a real noneditable wheel CI smoke, `scripts/wheel_manifest.py` with full exact commit SHA and wheel SHA256, a prepared local dependency wheelhouse and a no-index installation test. Actions artifacts expire after 30 days; their URIs are not durable release coordinates.

ORAEC-TF has already exercised a wheelhouse built from a full pinned tf-build source revision and real installed TF writer/CLI tests, but its wheel's direct VCS dependency prevents ordinary cold offline resolution through a stable versioned package.

## Decisions

- Choose `0.1.0rc1` as a **candidate** package version. Tag `v0.1.0rc1` must point to the reviewed package commit; a PR changing the version does *not* itself authorize a tag, asset publication or downstream migration.
- Extend existing wheel manifest validation (not a parallel manifest format): optionally read the real built sdist `tf_build-0.1.0rc1.tar.gz` with stdlib tarfile, inspect its root `PKG-INFO` as metadata (without extraction or code execution), and bind its exact raw bytes with SHA256. Reject incompatible/multiple wheels and sdists, member path traversal, symlinks, metadata disagreement, and incorrect tag/version. Continue supporting the existing dev-wheel manifest calls.
- CI builds wheel and sdist from the same exact PR source checkout, validates versions/digests, runs existing noneditable wheel/install tests, retains 30-day development evidence.
- A **manually dispatched** release workflow takes an existing exact version tag, verifies that it resolves to a commit reachable from main, checks out that commit, verifies successful main-branch CI on that exact commit, re-runs the package checks, then publishes a prerelease using repository GitHub token under a `release` environment and limited contents:write. The workflow must not run merely because a PR merged.
- GitHub environment protection / immutable tag and release settings must be configured by repo owners separately. Workflow-dispatch and environment approval are publication controls, but are not the same as cryptographic signing or provenance attestations.

## Non-goals and limitations

A development PR cannot prove that a future release was actually published. Do not fabricate asset URLs, hashes, or release success. Hash inventory of wheelhouse transitives produced on Ubuntu 3.12 is not a cross-platform lock. No change to ORAEC-TF direct URL until durable assets exist and downstream real offline resolver test passes. Source-package license is MIT; corpus licensing is separate.
