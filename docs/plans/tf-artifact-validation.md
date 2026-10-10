# Plan: typed TF artifact validator

Issue: #6

## Public API (initial)

```python
ValidationLevel = Literal["metadata", "selected", "all"]
FeatureKind = Literal["node", "edge", "config"]

@dataclass(frozen=True, slots=True)
class FeatureRequirement:
    name: str
    kind: FeatureKind | None = None
    value_type: Literal["str", "int"] | None = None
    edge_values: bool | None = None

@dataclass(frozen=True, slots=True)
class ArtifactValidation:
    level: ValidationLevel
    feature_names: tuple[str, ...]
    required_features: tuple[str, ...]

class ArtifactValidationError(ValueError): ...

def validate_tf_artifact(
    directory: str | Path,
    *,
    required_features: Collection[FeatureRequirement] = (),
    level: ValidationLevel = "selected",
    require_otext: bool = False,
) -> ArtifactValidation: ...
```

## Invariants / behavior

- Directory must exist, be a directory and not itself be a symlink.
- `otype.tf` and `oslots.tf` are present as ordinary files; `otext.tf` only when requested.
- Reject symlinked `*.tf` files; do not traverse into adjacent modules or compiled `.tf/` cache.
- A fresh `Fabric(locations=[directory], silent="deep")` is created for every call.
- `Fabric.explore()` supplies the discovered feature set; fail on absent requirements or metadata-load errors.
- Kind, `valueType`, `edgeValues` are checked only when explicitly specified.
- `metadata` does not call `Fabric.load`; `selected` calls `Fabric.load` for required node/edge features; `all` subsequently calls `Fabric.load(..., add=True)` for all discovered node/edge features and checks returned success.
- Selected/all return success only if Text-Fabric returns a live API rather than `False`/None.
- Validation result records `level`, all available file-backed feature names, and names explicitly required.
- No fixed corpus slot/node ontology, no required text format names.

## RED-first test set

1. actual small `Fabric.save` dataset: metadata, selected, all pass and report proper levels;
2. node `str`/`int`, unvalued/valued edges, and `otext` config metadata contract checks;
3. missing required feature and wrong kind/value type/edge-values fail;
4. missing warp or required `otext` fail;
5. corrupt requested feature data fails selected/all, while metadata-only does not falsely claim a reload;
6. corrupt unrequested feature body is detected by all but not necessarily selected;
7. symlinked feature file and symlinked artifact directory fail without following target;
8. duplicate requirements and invalid level/name policies fail;
9. real TF API available in synthetic integration test to confirm reload rather than metadata-only inspection.

## Gates

Document RED first (module missing), implement minimal code, run real integration tests, full pytest/Ruff/strict mypy CI on Python 3.11–3.14, logically independent adversarial review on exact head. Every behavioral review fix repeats relevant gates.
