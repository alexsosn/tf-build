# Research: structured operational build/provenance reports

Issue: #5

## Consumer evidence

### CopticScriptorium-TF

`ConversionResult` currently records:

- source record count;
- slot/node/edge counts;
- final output path;
- TF file count and bytes;
- parse/graph/write timings;
- peak RSS;
- a corpus-specific list of records missing literal licence metadata.

Its Agora adapter rewrites the absolute output path to the stable relative path `tf` before publishing `conversion-summary.json`.

This shows a reusable operational core, but also two things the shared package should improve:

1. absolute local paths are not portable provenance;
2. corpus-specific diagnostics such as licence-record IDs should remain consumer-owned rather than forcing an extension bag into the shared schema.

### TLHdig-TF

TLHdig's `BUILD-MANIFEST.json` has a different role. It binds exact/normalized input, code and output identities plus successful validation gates. Its output tree digest is a closed-world verification mechanism.

That is **not** an operational run report. Artifact fingerprinting/identity belongs to #7. Merging the two concepts would make ordinary timing/statistics output look like release certification.

## Model boundary

The shared report should be a deterministic serialization of a typed in-memory result, but independent builds are not expected to produce byte-identical reports because timings/resource use naturally vary.

The report may contain:

- producer package/name and version;
- declared immutable Git source provenance;
- ordered phase timings;
- one or more logical artifact summaries;
- optional process resource usage;
- small named numeric operational metrics.

It must not contain:

- arbitrary JSON extension blobs;
- absolute local source/output paths;
- corpus semantic records needed to query the corpus;
- file digests or release-certification claims;
- a wall-clock timestamp by default.

## Source provenance

For the first API, support only evidence already implemented by tf-build: Git.

A `GitSourceProvenance` records:

- declared repository locator;
- canonical full 40/64-hex revision;
- object format derived from revision length.

The repository locator is caller-declared provenance. tf-build does not claim that `verify_git_source` proved ownership by that remote.

Archive/DOI provenance should be added only with a real acquisition/verification consumer.

## Artifact paths

Artifact paths in a report are logical POSIX-relative paths such as `tf`, `tf/0.4.0`, or `tf-provenance/0.4.0`.

Reject absolute paths, `.`, `..`, empty components and backslashes. A build host can therefore serialize the same logical path regardless of its temporary checkout/workspace root.

## Metrics and diagnostics

A small numeric metric abstraction is justified for repeated operational counts such as slots/nodes/edges/source records. Metric names must be unique and values finite/non-boolean.

Do not add generic diagnostics/details objects in schema 1. Consumer-specific anomaly reports remain separate or wrap the core report.

## Resource measurement

Coptic's peak RSS helper uses the standard `resource` module but emits `0.0` when unavailable. Shared behavior should use `None` for unavailable data.

Known units:

- macOS: `ru_maxrss` is bytes;
- Linux: `ru_maxrss` is KiB.

For other platforms, return `None` rather than guessing the unit.

## Serialization

- schema version is explicit;
- field/key names are stable;
- lists preserve semantic order;
- JSON object keys are sorted;
- UTF-8 / `ensure_ascii=False`;
- one trailing newline;
- NaN/Infinity are rejected.

The report is safe to write outside the TF artifact. It is operational metadata, not a semantic sidecar.
