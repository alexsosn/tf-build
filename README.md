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
