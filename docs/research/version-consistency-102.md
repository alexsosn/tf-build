# Release version consistency (#102)

## Research (2026-10-28; before tests or production changes)

- `pyproject.toml [project].version` is `0.1.0rc1`, and the completed immutable release is `v0.1.0rc1` from commit `65a3bbb42a238f2cd59931cca79ee01560fdd887`.
- `src/tf_build/__init__.py` still exports `__version__ = "0.1.0.dev0"`; `tests/test_package.py` explicitly asserts that obsolete value.
- `scripts/check_installed_wheel.py::check_distribution` already reads `importlib.metadata.version("tf-build")` in genuine noneditable wheels, and checks import paths and actual Text-Fabric publication, but does not compare the imported package's `__version__` to that metadata. This allows false runtime provenance while the package filename, METADATA and wheel-manifest version are correct.
- `.github/workflows/ci.yml` installs editable checkout in Python 3.11–3.14; its distribution job separately builds direct and sdist-rebuilt wheels and runs `check_installed_wheel.py` from fresh environments, including offline wheelhouse install. `.github/workflows/release.yml` repeats the checked wheel smoke on owner-controlled publication, and refuses tag/version mismatches. None currently detects the exported runtime version defect.
- The released rc1 wheel must remain immutable; existing ORAEC-TF consumer pins `tf-build==0.1.0rc1` and has passed offline Linux/Windows checks. Those CI checks do not imply a correct `tf_build.__version__` attribute. No silent rebuild or tag overwrite is appropriate.
- README currently describes rc1 publication and ORAEC consumer migration as pending, although both completed. This is misleading for users preparing installations.

## Plan and acceptance

1. **RED first**: replace the obsolete version-constant-only test with assertions comparing exported `tf_build.__version__` to the checkout's `pyproject.toml [project].version` (read with stdlib `tomllib`) and editable installed distribution metadata. Observe the expected failing test against unchanged production sources and record actual exact-head CI logs.
2. **GREEN**: increment the next unpublished candidate metadata to `0.1.0rc2` and align the single exported literal. Add an equality guard to the existing installed-wheel checker so both direct and sdist-rebuilt wheel installation paths enforce the contract. Keep the API backward compatible; no dynamic metadata loading at import time, new dependencies, release/tag creation or consumer pin changes.
3. Correct README's release status and historical instructions, disclosing that immutable rc1's `__version__` erroneously reports `0.1.0.dev0`, and that rc2 remains unreleased until the owner-controlled release gate.
4. Run exact-final-head Python 3.11–3.14 lint/type/pytest, genuine direct/sdist/offline wheel smoke (including actual TF publication), inspect jobs, then conduct a logically separate skeptical review of the frozen diff against artifact provenance and real ORAEC consumption. Merge only if green.

## Explicit limits

The update repairs **future source and distribution artifacts only**; it cannot retroactively change rc1 bytes, replace existing tags, attest scientific correctness, or guarantee downstream consumers inspect the package's runtime attribute. Static `__version__` remains a duplicated version field, but the release gates now detect drift rather than importing installed-package metadata at import time (which could break direct checkout imports).
