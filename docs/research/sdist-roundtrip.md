# Research: source distribution installability gate

Issue #62, supporting upstream prerelease issue #60 and downstream ORAEC-TF #59.

## Actual pipeline gap

After #61, `.github/workflows/ci.yml` builds a wheel and `tf_build-0.1.0rc1.tar.gz` sdist. The stdlib manifest checks the source tarball's filename, PKG-INFO/version, safe archive members and SHA256. `scripts/check_installed_wheel.py` tests the *direct checkout-built wheel*, but no installation/rebuild is attempted from the actual sdist. A source tarball with valid metadata and a missing `src/tf_build/publication.py` could pass the current sdist metadata gate but fail when a downstream consumer builds from the source archive.

The manual `release.yml` repeats the same asymmetry and is designed to publish a durable prerelease artifact only after a protected manual dispatch.

## Decision

Within existing distribution/release workflows only, run `pip wheel --no-deps --wheel-dir <separate-dir> <actual generated sdist .tar.gz>`. Install that independently rebuilt wheel into a separate fresh virtualenv and invoke `scripts/check_installed_wheel.py` with current source checkout path so imports from the checkout are rejected. The smoke imports the installed `tf_build.publication`, `source`, `validate`, `report` and other public entry points.

Keep separate filenames/directories for the original checkout-built wheel and rebuilt wheel; never compare wheel-byte hashes because PEP 517 builds may differ in incidental archive metadata. The emitted release manifest should still hash the **original release wheel and original sdist**, not the reconstructed verification wheel.

Building the sdist wheel can install build dependencies from network and is therefore an *installability proof*, not an offline-source-build claim. Exact cold-offline installation of the published locked consumer wheel remains a separate ORAEC release gate.
