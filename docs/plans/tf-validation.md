# Plan: Text-Fabric artifact clean-reload validation

Issue: #6

## Public API

Add `tf_build.validation`:

```python
FeatureRequirement(
    name: str,
    kind: Literal["node", "edge"],
    value_type: Literal["str", "int"] | None = None,
    edge_values: bool | None = None,
)

TFArtifactContract(
    features: tuple[FeatureRequirement, ...] = (),
    text_formats: tuple[str, ...] = (),
    section_types: tuple[str, ...] | None = None,
    section_features: tuple[str, ...] | None = None,
)

TFValidationResult(
    mode: Literal["selective", "exhaustive"],
    node_features: tuple[str, ...],
    edge_features: tuple[str, ...],
    text_formats: tuple[str, ...],
    section_types: tuple[str, ...],
    section_features: tuple[str, ...],
)

validate_tf_artifact(
    path: str | Path,
    *,
    contract: TFArtifactContract = TFArtifactContract(),
    mode: Literal["selective", "exhaustive"] = "selective",
) -> TFValidationResult
```

Use a dedicated `TFValidationError(RuntimeError)` for artifact/contract failures.

## Contract validation

- feature names must be non-empty single TF feature names, not paths/whitespace lists;
- feature requirements must be unique;
- `edge_values` is valid only for edge requirements;
- text-format names must be non-empty and unique;
- section types/features must be supplied together, have equal length, and contain 1-3 non-empty names;
- mode must be exactly `selective` or `exhaustive`.

## Artifact preflight

- root must be a real directory and not a symlink;
- `otype.tf` and `oslots.tf` must be regular non-symlink files;
- every required feature's `<name>.tf` must be a regular non-symlink file;
- `otext.tf` is required when text-format or section expectations are present.

Instantiate `Fabric(locations=str(root), silent="deep")`, run metadata exploration, and compare feature kind/type/edge-values before expensive runtime loading.

## Runtime validation

Selective:
- fresh `Fabric.load()` requesting only contract feature names;
- resolve the returned API robustly if Text-Fabric returns an API object versus a truthy compatibility value;
- use `api.isLoaded(pretty=False)` to confirm required feature runtime information.

Exhaustive:
- fresh `Fabric.loadAll()`;
- reject false/absent API;
- all loadable node/edge features must survive full loading.

After either mode:
- required text formats must exist in `api.T.formats`;
- optional expected section type/feature tuples must match `api.T.sectionTypes` / `api.T.sectionFeatures`;
- build deterministic sorted feature-name tuples for the result.

## Cache cleanup

Always call Text-Fabric cache cleanup in `finally` after runtime loading starts.

Tests must prove:
- successful validation leaves substantive feature bytes unchanged;
- compiled `.tfx` files are absent after success;
- compiled cache is also cleaned after a validation error raised after loading;
- cleanup failure with no primary error raises `TFValidationError`;
- cleanup failure alongside a primary error is attached as an exception note while the primary error remains primary.

## RED-first tests

Use real tiny TF datasets written with supported Text-Fabric APIs; do not fake Fabric.

At minimum:

1. selective validation succeeds for a tiny corpus with node+edge features, one text format and one section level;
2. result explicitly reports `selective`;
3. exhaustive validation succeeds and reports `exhaustive`;
4. missing `otype.tf` / `oslots.tf` fails;
5. symlinked required feature fails closed where symlinks are available;
6. missing required feature fails;
7. wrong node/edge kind fails;
8. wrong `valueType` fails;
9. wrong `edgeValues` expectation fails;
10. missing required text format fails;
11. mismatched expected section tuple fails;
12. a malformed required feature that Text-Fabric cannot load fails;
13. a malformed *unrequired* extra feature may pass selective mode but fails exhaustive mode, demonstrating the documented level distinction;
14. contract duplicate/invalid names fail before loading;
15. feature-file bytes are unchanged across validation;
16. no compiled `.tfx` cache remains after success/failure.

## Exact-head gates

- focused validation tests;
- full pytest;
- Ruff;
- strict mypy;
- Python 3.11-3.14 CI;
- independent adversarial review grounded in actual Text-Fabric behavior and at least the Coptic/TLHdig usage patterns.
