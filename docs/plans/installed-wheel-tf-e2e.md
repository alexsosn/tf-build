# Issue #98 — implementation and TDD plan

1. Record research and plan before changes. Stay within `scripts/check_installed_wheel.py` and a focused pytest file; both CI and release workflows already execute that exact checker.
2. RED-first: create temporary fake checkout containing an example that exits unsuccessfully, and another that reports success but emits no TF artifact. Call the current checker's `check_distribution(fake_checkout)`; it currently returns successfully without running either example. Confirm a real pytest assertion failure on unchanged production, not an import/collection/lint error.
3. Add minimal `_check_publication_example` and invoke it after installed public APIs verify, using a fresh isolated `TemporaryDirectory`, `sys.executable -I` and `cwd` outside source, with bounded subprocess timeouts.
4. Validate output independently: required native TF files, provenance report, stdout fingerprint, full source-only TF reload, real `Fabric` word and valued-edge API queries. Rerun to assert existing-destination no-clobber and unmodified fingerprint.
5. Add positive pytest using a temporary checkout with a copy of the *real existing example*. No new TF writer or serialization abstraction.
6. Freeze head. Require GitHub Actions Ruff, mypy, Python 3.11–3.14 pytest, distribution direct/sdist/offline installed-wheel gates, and public producer audit on exact PR commit. Inspect actual distribution job logs to confirm E2E ran **after installed wheel**.
7. Logically independent adversarial review of final actual diff, including no editable checkout imports, true TF data query, broken-example RED, no-clobber and release workflow behavior. Merge only on complete GREEN. This must not publish any tag or release.
