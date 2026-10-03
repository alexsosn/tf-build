# Plan: structured operational build report

Issue: #5

## Public API

Add `tf_build.report` with immutable dataclasses:

```python
Producer(name: str, version: str)
GitSourceProvenance(repository: str, revision: str)
PhaseTiming(name: str, seconds: float)
ArtifactSummary(path: str, files: int, bytes: int)
Metric(name: str, value: int | float, unit: str | None = None)
ResourceUsage(peak_rss_bytes: int | None)
BuildReport(...)
peak_rss_bytes() -> int | None
```

`BuildReport.to_dict()` and `BuildReport.to_json()` provide the schema-1 machine representation.

## Validation

- all names/versions/locators are non-empty strings;
- Git revision uses `validate_git_revision`;
- Git repository provenance rejects local absolute/home/file locators so reports do not capture machine-specific source paths;
- logical artifact paths are normalized POSIX-relative paths with no POSIX/Windows absolute form, traversal, or backslashes;
- counts and byte sizes are non-negative integers and not bool;
- timing/float metrics are finite and non-negative where required;
- metric, phase and artifact paths are unique;
- no arbitrary extension dictionary exists in schema 1.

## JSON shape

```json
{
  "schema": 1,
  "producer": {"name": "...", "version": "..."},
  "source": {
    "kind": "git",
    "repository": "...",
    "revision": "...",
    "objectFormat": "sha1"
  },
  "phases": [{"name": "parse", "seconds": 1.25}],
  "artifacts": [{"path": "tf", "files": 42, "bytes": 12345}],
  "metrics": [{"name": "slots", "value": 1000, "unit": null}],
  "resources": {"peakRssBytes": 123456}
}
```

`source` and `resources` may be null; lists may be empty.

## RED-first tests

1. canonical Git provenance for SHA-1/SHA-256;
2. invalid symbolic revision rejected;
3. absolute/traversing/backslash artifact paths rejected;
4. negative/bool counts rejected;
5. NaN/Infinity and negative timings rejected;
6. duplicate phase/artifact/metric names rejected;
7. same report object serializes byte-for-byte deterministically with sorted keys and trailing newline;
8. no absolute local paths appear in a representative Coptic-shaped report;
9. peak RSS helper returns positive bytes on Linux/macOS and `None` where units are unknown.

## Non-goals

- writing report files atomically (can compose with workspace/_atomic later);
- output/input digests (#7);
- validation certification;
- consumer-specific anomaly payloads;
- timestamps.

## Exact-head gates

Full pytest, Ruff, strict mypy, Python 3.11–3.14 CI, then independent adversarial review against real Coptic/TLHdig contracts.
