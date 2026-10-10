# Plan: runnable Text-Fabric publication smoke

Issue: #26

## Deliverable

`examples/tiny_tf_publication.py` with `main(argv: list[str] | None = None) -> int` and CLI `python examples/tiny_tf_publication.py OUTPUT`. This is an example only, not an entrypoint, generic writer or safety wrapper.

Pipeline:

1. Require an absent final destination using `BuildWorkspace`; private staging is beside final path.
2. Serialize real `otype`, `oslots`, `otext`, `wordText` and a valued `attestation` edge using `Fabric.save`.
3. Reload every feature via `validate_tf_artifact(level="all", require_otext=True, required_features=...)`.
4. Write an operational `BuildReport` to `run-report.json` inside staging; do not include a digest or call it a certificate.
5. Fingerprint all shipped files using `fingerprint_tree`, excluding only TF compiled `.tf/` caches.
6. Publish once, independently fingerprint the published tree, and verify identity equality. Emit concise JSON on stdout.

## RED-first tests before example implementation

- Subprocess invocation of the absent example must fail before implementation, pass afterward. Assert persisted warp, config, node feature, valued edge and report, and inspect stdout fingerprint against independent `fingerprint_tree`.
- Reinvoke same CLI destination: fail without changing first published identity or bytes.
- A separate deliberately malformed real `count.tf` integer body triggers `validate_tf_artifact(level="all")` before `BuildWorkspace.publish`. Context exit cleans staging, no artifact appears, and sibling committed tree retains its fingerprint.
- Confirm compiled `.tf/` caches do not perturb source fingerprint on revalidation.

## Gates

Tests committed before example code; exact-head Python 3.11–3.14 CI Ruff/mypy/pytest; separate skeptical code review checking failure/cleanup and claim boundaries. Avoid a new public library API.
