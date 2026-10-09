# tf-build

Reusable build and materialization infrastructure for [Text-Fabric](https://github.com/annotation/text-fabric) corpus projects.

**Status: pre-0.1 bootstrap.** Public APIs are not yet stable.

## Scope

tf-build is intended to centralize infrastructure that is currently repeated across independent Text-Fabric conversion projects:

- immutable source identity and acquisition;
- safe staging and artifact publication;
- build/provenance reports;
- Text-Fabric artifact validation and deterministic fingerprints;
- reusable Agora materializer host glue;
- generated feature-reference infrastructure.

Corpus projects remain responsible for their source parsers, scholarly canonical models, normalization rules, slot type, node/edge ontology, text formats and source-specific documentation.

tf-build does not aim to replace Text-Fabric's `CV.walk` / `Fabric.save`, and it does not duplicate Text-Fabric-Factory's generic XML/TEI/PageXML conversion stack.

See [research.md](research.md), [design.md](design.md), and [plan.md](plan.md) for the evidence, architecture boundary and development sequence.

## Operational build reports

`tf_build.report` provides typed success-run metadata without conflating it with artifact certification:

```python
from tf_build.report import (
    ArtifactSummary,
    BuildReport,
    GitSourceProvenance,
    PhaseTiming,
    Producer,
)

report = BuildReport(
    producer=Producer("my-converter", "0.1.0"),
    source=GitSourceProvenance(
        "example/upstream",
        "0123456789abcdef0123456789abcdef01234567",
    ),
    phases=(PhaseTiming("convert", 1.25),),
    artifacts=(ArtifactSummary("tf", files=42, bytes=123456),),
)

print(report.to_json())
```

Artifact paths are portable logical POSIX-relative paths. Reports deliberately contain no file digests or release-certification claims; deterministic artifact identity is a separate layer.

## Git source verification

The first reusable primitive verifies an already-local clean Git working tree without contacting a remote:

```python
from tf_build.source import verify_git_source

snapshot = verify_git_source(
    "/path/to/source",
    expected_revision="0123456789abcdef0123456789abcdef01234567",
)

print(snapshot.revision)
print(snapshot.repository_root)
```

Only full 40- or 64-hex commit IDs are accepted. Branches, tags, `HEAD`, abbreviations, dirty worktrees and consumer-specific unversioned sentinels are rejected.

Pinned acquisition is explicit and separate from conversion:

```python
from tf_build.source import fetch_git_source

snapshot = fetch_git_source(
    "https://github.com/example/upstream.git",
    "/path/to/fresh/source",
    revision="0123456789abcdef0123456789abcdef01234567",
)
```

Acquisition uses a sibling staging directory, verifies the detached checkout before publication, and supports both SHA-1 and SHA-256 Git repositories. Conversion code should still receive local inputs and remain network-free.

## Safe build workspace

Generated artifacts can be built and validated in a fresh sibling staging directory and published explicitly:

```python
from tf_build.workspace import BuildWorkspace

with BuildWorkspace("/path/to/final-artifact") as workspace:
    build_into(workspace.path)
    validate(workspace.path)
    workspace.publish()
```

The final destination must not already exist. Exiting the context without `publish()`, or leaving it through an exception, removes unpublished staging. Publication is atomic no-clobber on supported platforms; replacement of an existing artifact is intentionally a separate contract.

## Text-Fabric artifact validation

Use `tf_build.validate` to verify an emitted dataset independently of its
parser, with explicitly declared validation depth:

```python
from tf_build.validate import FeatureRequirement, validate_tf_artifact

result = validate_tf_artifact(
    "/path/to/generated/tf",
    level="selected",
    require_otext=True,
    required_features=(
        FeatureRequirement("lemma", kind="node", value_type="str"),
    ),
)
print(result.level, result.feature_names)
```

- `metadata`: inspect file-backed features and metadata contracts, but do **not**
  claim to have loaded the data.
- `selected` (default): independently reload TF warp and caller-required
  data features, including Text-Fabric's implicit text dependencies.
- `all`: load every discovered node/edge feature; use as a deliberate
  expensive release/integration gate for large corpora.

Slot/node ontology and source-semantic checks remain the corpus project's
responsibility. Runtime TF loading can create derived `.tf/` compiled caches;
validation never intentionally rewrites the original `.tf` feature files.
`otext.tf` is optional upstream; request it explicitly when
the consuming corpus requires it.

## Development

Python 3.11+ is the initial supported runtime. Text-Fabric 13.x is the initial compatibility target.

```bash
python -m pip install -e '.[dev]'
python -m ruff check .
python -m mypy
python -m pytest -q
```

Autonomous coding agents must start with [AGENTS.md](AGENTS.md). Every behavior-changing ticket follows research → plan/design → RED-first TDD → implementation → exact-head tests → logically independent adversarial review.

## License

MIT. This repository contains reusable software infrastructure; corpus/source data remain governed by their own projects and licences.
