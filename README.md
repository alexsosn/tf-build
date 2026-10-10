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

Git source provenance is a **public identifier**, not the credential-bearing URL
used for fetching. `GitSourceProvenance` accepts clean HTTPS and conventional
SSH/SCP-style repository locators but rejects HTTP(S) userinfo, URL passwords,
queries and fragments. Supply a separate sanitized repository locator when a
private source must be acquired with credentials; do not embed tokens in
exported build reports.


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

Git inspection and acquisition commands have a generous **30-minute per-command**
timeout by default, not an overall materialization deadline. Callers with
different transport requirements can override it:

```python
snapshot = fetch_git_source(
    "https://github.com/example/upstream.git",
    "/path/to/fresh/source",
    revision="0123456789abcdef0123456789abcdef01234567",
    timeout_seconds=900.0,
)
```

`verify_git_source(..., timeout_seconds=900.0)` accepts the same positive
finite value. Timeouts raise `GitSourceError` and unpublished acquisition
staging is cleaned. A direct Git command timeout does not necessarily stop
transport subprocess grandchildren or impose a global build deadline.


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

## Raw-byte artifact fingerprints

`tf_build.fingerprint` computes a versioned SHA-256 identity of every
regular shipped file under an artifact directory:

```python
from tf_build.fingerprint import fingerprint_tree

fingerprint = fingerprint_tree(
    "/path/to/generated/tf",
    manifest_path="BUILD-MANIFEST.json",
)
print(fingerprint.algorithm, fingerprint.digest)
```

The fingerprint uses **actual file bytes**. No TF timestamp/header normalization
occurs here; consumers requiring byte-reproducible output must normalize before
fingerprinting. Text-Fabric's derived `.tf/` compiled caches and the optional
explicit manifest file are excluded; all other regular files including licenses
and documentation contribute. Symlinks/nonregular entries fail closed.
Fingerprinting a concurrently changing directory is not an atomic snapshot.

## Agora materializer output helpers

`tf_build.agora` provides small preflight/path helpers for plugins running
inside Agora's existing private, empty output directory:

```python
from tf_build.agora import (
    agora_output_path,
    optional_source_revision,
    prepare_agora_output,
)

root = prepare_agora_output("/agora-output/output")
tf_child = agora_output_path(root, "tf")
revision = optional_source_revision("")  # None for user-local/archive input
```

Both direct TF output at `root` and nested TF output at `tf_child` are
supported. The optional source revision accepts only complete immutable Git
IDs when present. `agora-materialization.json` is reserved to Agora itself.

Agora, not tf-build, owns acquisition, sandbox/network enforcement, output
validation and final promotion. These helpers never create the host root,
execute conversion code or publish the user's destination.

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
responsibility. For `selected` and `all`, validation loads a private,
source-only view of the emitted `.tf` files so existing Text-Fabric `.tf/*.tfx`
binary caches cannot hide corrupted raw feature bodies. The view prefers
hardlinks (no duplicate source-byte storage) with a file-copy fallback, and
cleans up derived caches on exit. The artifact's own `.tf` files and compiled
caches are not intentionally changed; large datasets may require extra
temporary storage or I/O if linking is unavailable. This is not an atomic
snapshot under concurrent source mutation. `metadata` stays a cheap header
check. `otext.tf` is optional upstream; request it explicitly when
the consuming corpus requires it.

## Preflight for unsafe Text-Fabric string values

Text-Fabric 13.x escapes LF and TAB inside string feature values but writes
literal CR (U+000D) unchanged. Python's universal-newline text loading can
then silently shift a value onto another node. This occurred in a real ORAEC
bibliography feature; ordinary node counts and successful TF loads did not
prove attribution was correct.

Before using Fabric.save:

```python
from tf_build.tf_strings import preflight_tf_save_values

preflight_tf_save_values(node_features, edge_features)
# Fabric.save(nodeFeatures=node_features, edgeFeatures=edge_features, ...)
```

For CV.walk or per-value writers, use
`require_tf_safe_string(value, feature="text", node=word_node)`.
For valued edges pass a target node as well. Either preflight raises
`TFStringSafetyError` with feature/node context and no raw source value.
LF, TAB, backslashes and other supported strings are preserved exactly.
Consumers that need literal CR can encode it losslessly **in native TF
features** before preflight, then check source-to-TF roundtrip parity.
This preventive check neither patches Text-Fabric nor validates already
emitted .tf data or scholarly semantics.

## Generated Text-Fabric feature reference

`tf_build.feature_docs` scans **emitted** Text-Fabric feature-file headers
without loading corpus data, preserving unknown metadata and header markers:

```python
from tf_build.feature_docs import (
    render_feature_reference,
    scan_tf_feature_headers,
)

features = scan_tf_feature_headers({
    "core": "/path/to/tf/core",
    "provenance": "/path/to/tf/provenance",
})
pages = render_feature_reference(
    features,
    descriptions={("core", "lemma"): "Lexical headword"},
)
# pages["index.md"] and pages["core/lemma.md"] are deterministic Markdown.
```

The returned pages are **in memory**, leaving writing, drift detection and
publishing to the consumer. Module-qualified pages permit repeated feature
names across separately distributed TF modules. Plain-text semantic descriptions
are caller-owned; the original `@description` and other header metadata remain
visible. This does not infer supported-but-absent features or replace a clean
artifact reload/validation gate.

## Executable Text-Fabric publication smoke

The repository includes a minimal **real Text-Fabric** consumer showing how
to compose existing primitives without a new universal build runner:

```bash
python examples/tiny_tf_publication.py /tmp/new-tiny-tf
```

The destination must not exist. The script serializes word slots and a valued
edge using `Fabric.save`, independently reloads every TF feature, emits a
caller-owned operational `run-report.json`, fingerprints shipped raw bytes,
publishes with `BuildWorkspace`, and verifies the published fingerprint.
Text-Fabric's compiled `.tf/` cache is not part of the source-byte identity.
Re-running against the same destination refuses to overwrite it.

It is a toy corpus, not an Agora host integration or a scholarly validation
claim; see `tests/test_publication_smoke.py` for the fail-closed corruption
and non-clobber checks.

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
