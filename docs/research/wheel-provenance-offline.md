# Research: wheel provenance and offline consumer installation

Issue #58; parent #53; ORAEC-TF consumer #59.

## Current evidence

`pyproject.toml` currently builds package `tf-build` at version `0.1.0.dev0` with `setuptools>=75` and `text-fabric>=13.1,<14` as the sole declared runtime dependency. `.github/workflows/ci.yml::distribution` runs `pip wheel --no-deps`, then a real noneditable venv install and the `scripts/check_installed_wheel.py` imports/safety smoke outside the checkout. The wheel and resolved dependency bytes are discarded on runner completion; no `actions/upload-artifact` step exists and GitHub Releases lists no assets. ORAEC-TF has been installed from a full immutable Git revision, which is reproducible at source fetch time but requires Git/network for installation.

A wheel artifact must be bound to the **actual checkout tree SHA** and exact wheel-byte SHA256, not just a mutable Actions artifact name. `GITHUB_SHA` for a pull_request event may refer to a synthetic merge commit; a distribution checkout of `github.event.pull_request.head.sha || github.sha` makes the recorded source identity the literal PR source SHA. All four Python matrix jobs still verify their normal PR checkouts.

## Decisions

- Add a tiny no-dependencies manifest generator that reads actual `pyproject.toml` and the built wheel's `*.dist-info/METADATA`, verifies name/version, computes the SHA256 of the wheel bytes, and writes canonical deterministic JSON with full Git source SHA and filename. Never invent a release tag or assert that CI output is signed.
- Keep the existing noneditable-installed-wheel smoke and add a separate wheelhouse download step **while CI has network access**, followed by `pip --no-index --find-links` installation in a fresh venv outside checkout. This demonstrates *offline installation given prepared local wheel files*, not that the wheelhouse's transitive dependencies are frozen across builds.
- Upload the tested `tf_build` wheel, its manifest, and the temporary wheelhouse with SHA256 inventory for a short 30-day Actions retention period. This is development evidence, not a durable package index/release.
- No PyPI/release credentials or automatic publication. Licensing, stable semver, permanent digest-pinned release and platform-specific dependency lock remain explicit next steps and must not be silently marked complete.

## Trust boundaries

A manifest produced in CI is not a signed attestation. Verify the hashes after download and bind them to the CI run/source SHA. Wheels with multiple matching distribution files, inconsistent embedded metadata or malformed Git revision must fail closed before manifest output. Avoid loading arbitrary wheel Python modules while inspecting metadata: use only zipfile metadata bytes.
