# Plan: versioned wheel/sdist release gate

Issue #60; current ticket covers the upstream release-readiness PR, not unverified publication.

1. RED-first stdlib tests: construct synthetic wheel and real tar.gz sdist with matching `PKG-INFO`; require exact source commit, tag version `v<package version>`, raw SHA256 for both assets, and no unexpected archive members. Test multiple/missing archives, malicious tar member traversal or symlink, mismatched filename/metadata and incorrect release tag. Keep previous development-artifact manifest contract.
2. Implement narrowly in the existing `scripts/wheel_manifest.py`: optional `sdist_dir` / `release_tag`; keep the resulting deterministic canonical JSON and exclusive write. Bump `pyproject.toml` to `0.1.0rc1`. No new package API or corpus semantics.
3. Extend `.github/workflows/ci.yml` distribution job to build/test an sdist in addition to the wheel and retain both as artifact; require version/tag/digest manifest on the same exact PR head. Preserve isolated offline wheelhouse install gate.
4. Create a **manual-only** prerelease workflow that resolves an already created immutable version tag, verifies tag→commit and main ancestry, checks out/builds/tests release input and publishes with `gh release create --verify-tag --prerelease` using limited permissions and a release environment. No automatic tag creation, no overwrite of an existing release and no unreviewed source building.
5. Document exact after-merge operator approval/tag, release asset digest-verification and downstream ORAEC dependency-lock migration steps. Do not claim the issue complete or close #60 until actual durable publication and offline consumer test.
6. Exact-head Ruff, mypy, pytest across Python 3.11–3.14 plus distribution CI and independent adversarial review. Any fix after final review reruns checks. If connector can't securely publish release assets, stop at reviewed ready-to-publish gates rather than asserting publication.
