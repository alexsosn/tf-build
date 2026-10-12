# Context-Fabric producer acceptance pilot

The public non-fork TF producer inventory (in `policy/public-tf-producers.json`)
requires an additional **PR-triggered** Context-Fabric test for:

| Producer | Acceptance workflow | Full-corpus follow-up |
| --- | --- | --- |
| CATSS-TF | `.github/workflows/context-fabric-acceptance.yml` | [#125](https://github.com/alexsosn/CATSS-TF/issues/125) |
| IIP-TF | `.github/workflows/context-fabric-acceptance.yml` | [#105](https://github.com/alexsosn/IIP-TF/issues/105) |
| ORAEC-TF | `.github/workflows/context-fabric-acceptance.yml` | [#88](https://github.com/alexsosn/ORAEC-TF/issues/88) |

Each producer's dedicated Python 3.13 workflow converts a real native-TF
fixture and compares Text-Fabric 13.1 output against Context-Fabric's raw
`.tf` load and **fresh compiled memory-mapped `.cfm` reload**. It checks
representative slot/node types, node feature values (including missingness
where sampled), locality, edge features where present, representative search
results and immutable source-feature checksums. A missing `cfabric` runtime
must fail the dedicated workflow, not skip the suite.

This is **fixture-sized compatibility**, not whole-corpus CF equivalence,
publication readiness, or performance certification. The three full-corpus
follow-up issues must remain separately tracked. Researchers should not
substitute a green CI fixture for source-wide node/edge conservation.

IIP's fixture exposed a real bug in Context-Fabric 0.5.7: an all-empty TF
feature was advertised in the `.cfm` manifest without the corresponding
compiled files. The reviewed compiler fix is
[Context-Fabric fork PR #8](https://github.com/alexsosn/context-fabric/pull/8),
commit `900060ef04346af0738500cf13fc397b8087e0b8`. IIP's CI pins
that exact fork commit, while an official released fix and complete IIP
corpus acceptance remain tracked in [IIP #104](https://github.com/alexsosn/IIP-TF/issues/104)
and [IIP #105](https://github.com/alexsosn/IIP-TF/issues/105).

The central audit verifies that each producer continues to publish a
PR-triggered workflow with an executable acceptance command, an explicit
Context-Fabric import, and source-level raw/compiled parity probes.
It does **not** inspect the outcomes of remote workflow runs or prove
their test implementations remain semantically sound. Per-repository
branch protection and actual green CI must enforce execution.
