# Research: installed-wheel native TF validation CLI (#120)

Date: 2026-11-18.

## Observed code and consumers

- `src/tf_build/validate.py::validate_tf_artifact` already supports `metadata`, `selected`, and `all`. The exhaustive mode loads all emitted node/edge features from a source-only view, avoiding stale `.tf/*.tfx` caches. `require_otext` is opt-in because Text-Fabric does not require it for every corpus. The validator does not check scholarly meaning.
- `examples/tiny_tf_publication.py` writes an actual native word/sentence TF artifact via `Fabric.save`, with node and valued-edge features, and checks exhaustive reload before publication.
- `scripts/check_installed_wheel.py` verifies the isolated wheel imports and runs the example from a **checkout**. It currently has no installed-package command for a researcher to validate a separately supplied TF directory.
- `docs/consumer-adoption.md` records four merged corpus-project adopters (ORAEC-TF, IIP-TF, CopticScriptorium-TF, CATSS-TF). The proposed entry point accepts their emitted TF directories without incorporating any of their individual node ontologies.

## Smallest shared behavior

Provide an argparse wrapper around the *existing* validator, via `python -m tf_build validate PATH`. The default should be exhaustive (`all`) so a researcher who opts to inspect a corpus does not unintentionally skip most feature bodies. Make `--level metadata|selected|all` explicit, and make `--require-otext` opt-in. Print JSON with actual level and feature inventory so automated scripts can distinguish different checks.

Invalid paths, absent warp files, failed loads and inconsistent metadata must exit nonzero without emitting successful JSON. Do not blanket-catch all exceptions or hide programming errors. A clean, descriptive `ArtifactValidationError` is expected for detected invalid artifacts.

## Out of scope

No new TF parser, corpus-normalization layer, structural ontology, package console-script dependency, feature-requirement DSL or new validation algorithm. This is a thin way to access the already tested public API.

## Test evidence to gather

RED: real Tiny-TF fixture should fail `python -m tf_build validate ...` while the module entry point is absent. GREEN: genuine subprocess on a non-checkout working directory succeeds with `all` and produces parseable JSON, no writes to source `.tf`, and failure cases exit without a JSON success claim. Distribution CI must test the command against a freshly installed wheel.

## CI-discovered failure: upstream Text-Fabric prints to stdout

Exact-head [CI 44320585144](https://github.com/alexsosn/tf-build/actions/runs/44320585144) on `1ad2c0ff476030798464590f612f6d2d728ae353` ran real native-TF tests against Python 3.11–3.14. All four quality jobs reached **539 passed, one failed**. The failure was `test_researcher_default_catches_corrupt_unselected_feature`: the CLI exited nonzero as expected for invalid integer feature body `1\tNOT_AN_INTEGER`, but Text-Fabric printed `There was a fatal error! ... invalid literal for int()` to *stdout* before raising/returning a failed load. The installed wheel/sdist distribution job passed.

The existing `validate_tf_artifact` API handles failure correctly; adding a separate parser or accepting non-JSON stdout would weaken the researcher CLI contract. Upstream console emissions are an implementation detail of Text-Fabric and should be isolated at the CLI boundary only. Avoid globally changing the validator's public console behavior, which consumers might rely on. A short error on stderr plus no success JSON is the desired CLI behavior. A discard-only stdout sink avoids buffering potentially large feature-error chatter in memory.
