# Plan: ensure emitted tf-build sdist rebuilds and installs

Issue #62

1. RED-first static workflow regression requires the distribution and manual release workflows to each rebuild a **separate** wheel from the actual `$RUNNER_TEMP/sdist/tf_build-*.tar.gz`, install that wheel into a new venv outside checkout and execute `scripts/check_installed_wheel.py`. Assert that the original wheel path does not substitute for the rebuilt one.
2. Add the same narrow `Rebuild and smoke-install wheel from emitted sdist` Bash step to both workflows, preserving existing dependency manifests, wheel-only smoke, version/tag checks, prerelease approval and no-index wheelhouse test.
3. Run real CI distribution: successful PEP 517 sdist→wheel roundtrip with package import logs, and Python 3.11–3.14 lint/mypy/tests on exact head. If setup metadata or missing package files trigger a failure, fix the actual package layout and repeat.
4. Separate adversarial review of the source tarball contents, independent rebuilt-wheel install path, failure propagation and distinction between online build and offline install.
5. Do not publish a GitHub Release or close #60; owner manual approval/tag and downstream ORAEC offline lock remain required.
