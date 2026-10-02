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
