# Plan: generic TF feature-header inventory and reference

Issue: #9

## Public API

```python
class FeatureReferenceError(ValueError): ...

@dataclass(frozen=True, slots=True)
class FeatureHeader:
    module: str
    name: str
    kind: Literal["node", "edge", "config"]
    value_type: str | None
    edge_values: bool
    metadata: tuple[tuple[str, str], ...]
    markers: tuple[str, ...]

def scan_tf_feature_headers(modules: Mapping[str, str | Path]) -> tuple[FeatureHeader, ...]: ...

def render_feature_reference(
    features: Iterable[FeatureHeader],
    *,
    descriptions: Mapping[tuple[str, str], str] | None = None,
) -> dict[str, str]: ...
```

The scanner consumes **real files**, not the converter's schema. The renderer is pure and outputs `index.md` and `{module}/{name}.md` pages. Descriptions are caller-owned plain text, not arbitrary Markdown. Unknown feature-header metadata is kept verbatim in the records and safely escaped in Markdown output.

## RED-first tests

1. Actual tiny `Fabric.save` TF dataset with node, unvalued/valued edge and otext config: scan emits correct metadata and kinds.
2. Cache directory `.tf/` plus arbitrary `scratch.tf/` ignored; malformed `*.tf` regular files rejected; `*.tf` symlinks rejected.
3. Ignore body corruption during header scan (scan is *not* validation) and preserve original artifact bytes.
4. Unknown metadata and standalone header markers retained and rendered safely (including HTML/script/Markdown injection payloads).
5. No blank separator, missing first-line kind marker, conflicting primary markers, duplicated metadata keys and invalid kind-edge-value combinations rejected.
6. Two modules with duplicate feature stems both survive under namespaced paths.
7. Deterministic module/name ordering and exact-repeat page contents; no dependence on directory enumeration.
8. Incorrect module identifiers/names and duplicate input records fail, not silently overwrite output pages.
9. Optional descriptions from consumer override display prose but not the published artifact metadata.
10. Unterminated oversized headers fail within bounded inspection (256 Ki characters total; 64 Ki per line).

## Implementation

Standard-library `pathlib` and streaming UTF-8 text headers. Keep scanning output immutable and all writing out of scope. No dependency on Text-Fabric runtime beyond tests' real fixture creation.

## Quality gates

Committed research + plan, RED-first real TF tests, implementation, GitHub Actions Python 3.11–3.14 Ruff/strict mypy/pytest on exact head, logically independent adversarial review grounded in actual emitted `.tf` files. Keep draft until GREEN and review.
