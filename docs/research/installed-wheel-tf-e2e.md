# Issue #98 — installed-wheel E2E publication contract

## Evidence from current source and real CI

At main commit `cf9769b2ee5b1d37400c5cfbb71572b7b7115bc7`, `scripts/check_installed_wheel.py::check_distribution` verifies package metadata, noneditable import location, public API presence, immutable SHA normalization and CR string preflight. It never uses Text-Fabric to serialize, load, query or publish an artifact. Both `.github/workflows/ci.yml` and manually approved `.github/workflows/release.yml` already call this script using the **newly installed wheel's interpreter** from outside the checkout. The CI distribution job uses it for direct wheels, rebuilt-from-sdist wheels and a no-index wheelhouse install.

The repository has a working real user-facing `examples/tiny_tf_publication.py` (word slots, sentence, valued attestation edge, source-only all-feature validation, build report, deterministic fingerprint, create-only publication). `tests/test_publication_smoke.py` runs it from normal pytest; the quality job installs `-e '.[dev]'`, so this cannot alone prove the wheel's complete runtime behavior. A verified wheel can import all checked names but still fail the actual installed-publication use case.

There is no need for a new CLI, converter, dependency or CI job. Add the E2E to the existing **installed-wheel checker**, so all existing call sites share the same gate. Execute the checked-out example script only from the trusted current repository head (the CI scripts already execute it in quality tests), from an unrelated temporary working directory, with the wheel virtualenv Python in isolated `-I` mode. The already-present `module_path.is_relative_to(checkout)` check remains a release prerequisite.

## Independent expected output oracle

On a fresh output root, the example must produce `otype.tf`, `oslots.tf`, `otext.tf`, `wordText.tf`, `attestation.tf` and `run-report.json`. Independently reload with installed `tf.fabric.Fabric` to retrieve word 1 = `hello`, word 2 = `world`, and valued `attestation` from sentence node 3 to slot 1 = `example`. Independently run installed `tf_build.validate.validate_tf_artifact(level="all")`, and compute an actual file-byte fingerprint matching the sample's stdout. Rerun with the same destination: it must refuse to overwrite and leave bytes unchanged.

Do not claim corpus-specific scholarly validation, ORAEC installed-wheel acceptance, an immutable dependency lock, or official release publication from this toy corpus. Release #60 and consumer #53 remain open.
