# Research: actual tf-build consumer adoption (issue #113)

Baseline 2026-11-16. The original project objective requires *production* use in multiple independent converter packages, not a simulated import or one self-consuming example.

## Verified code paths and packages

1. **ORAEC-TF (merged / production).** Current `src/oraec_tf/source.py` imports and calls `tf_build.source.validate_git_revision`, `verify_git_source` and `fetch_git_source` in real source acquisition, verification and pinned reproducibility. Current `src/oraec_tf/cli.py` invokes `tf_build.workspace.BuildWorkspace` and `tf_build.validate.validate_tf_artifact` in conversion. Current `src/oraec_tf/agora.py` calls `tf_build.publication.publish_path_no_clobber` for final staged native TF publication. `pyproject.toml` declares rc1; `requirements/tf-build.txt` points at exact published GitHub v0.1.0rc1 wheel with verified SHA256.
2. **IIP-TF (merged / production).** `src/iip_tf/agora.py::materialize` calls `tf_build.agora.prepare_agora_output(output)` at the real host boundary. `pyproject.toml` records a direct SHA256-locked GitHub v0.1.0rc1 wheel. [IIP PR #114](https://github.com/alexsosn/IIP-TF/pull/114) merged as `7245dd624a4e24538b5f5a673e5a4e6fe4e1a6d0`; exact-head 420 unit tests, full pinned 5,535-record EpiDoc→TF, installed Agora/browser acceptance and compiled Context-Fabric checks were green before guarded merge.
3. **CopticScriptorium-TF (proposed, not merged).** [PR #198](https://github.com/alexsosn/CopticScriptorium-TF/pull/198) head `85d9da23ea5597bbbedfcb5b654f0ea700df54f0` uses `tf_build.agora.prepare_agora_output` in `copticscriptorium_tf/agora.py`, and `tf_build.publication.publish_path_no_clobber` reexported by `_atomic.py` for both native dataset and summary; `pyproject.toml` includes the same SHA256-locked rc1 wheel. Real installed-browser 11,300 words, 6,521-word Agora sandbox, and 771 research tests passed. Full streamed Coptic↔LXX CI on #198 failed only at a **stale status-census expectation**, not a reported writer crash: `ambiguous=152` after merged #203 correction vs expected 52. The *subsequent* #205 full-source audit [43699229832](https://github.com/alexsosn/CopticScriptorium-TF/actions/runs/43699229832) established 220 after an additional 68 source2 slots. [Coptic issue #207 / draft PR #208](https://github.com/alexsosn/CopticScriptorium-TF/pull/208) corrects that verification baseline. #198 remains **unmerged**, and a new exact-head full CI/independent review is mandatory.

The release is an immutable **GitHub Release wheel**, not a verified PyPI package. Its SHA256 is `dff2a14c0299422b4716217d04e6d43b47e714f4dacdb21d9939292051e82c9a`. The released rc1's exported `tf_build.__version__` disagrees with distribution metadata; `0.1.0rc2` fixes that in source but is **unpublished**. Consumers should not assume rc2 or generic `pip install tf-build` from PyPI works.

## Evidence not sufficient for counting as active consumers

- CATSS-TF and PG-TF are targeted future audits, **not verified production consumers** here.
- ORACC-TF and Pseudepigrapha-TF declare Python 3.10 compatibility in the prior issue #112 audit, whereas current tf-build requires 3.11+. Do not unconditionally add a dependency that removes Python 3.10 support.
- A test import, docs example, install in developer tooling, unmerged PR, or feature similarity without actual converter call site **does not count** toward merged production adoption.

## Plan

Publish a single user-facing matrix with per-repository production call, install pin, evidence and state; link it from README. A main-branch 404 for `docs/consumer-adoption.md` is the observed documentation RED. Verify all assertions against actual source/PR and current main. No new generic API or CI inventory machinery. Human review must challenge every claim, especially a proposed integration being presented as merged.

Only close parent #112 when pending Coptic adoption and truthful docs are completed, not on the basis of a doc-only PR.
