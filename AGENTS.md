# tf-build agent instructions

tf-build is designed for autonomous, issue-driven development. Coding agents must treat this file as the mandatory entry point.

## Read first

Before changing behavior, read in order:

1. `README.md`
2. `research.md`
3. `design.md`
4. `plan.md`
5. `docs/agentic-dev-loop.md`
6. the active GitHub issue and all linked PR/review discussion

When work depends on Text-Fabric, Text-Fabric-Factory, Agora, or a consumer converter repository, verify the current contract against actual code/data/documentation rather than relying on memory.

## Development gates

Every behavior-changing ticket follows:

**research → plan/design → RED-first TDD → implementation → exact-head tests → logically independent adversarial review**

- Work from a GitHub issue with explicit acceptance criteria.
- Check open issues/PRs for overlap before starting.
- Ground abstractions in real consumer code; do not invent generic hooks speculatively.
- Record material research before implementation.
- Add a deterministic failing test before production behavior whenever the change is testable.
- Implement the smallest coherent contract that satisfies the researched need.
- Run the complete relevant suite on the exact final head.
- A review is valid only for the exact reviewed head. Any production-code change after approval invalidates it.
- Behavior-changing review fixes repeat RED → fix → GREEN → re-review.
- Review must be skeptical and evidence-driven, preferably exercising at least one real consumer pattern.
- Merge only after acceptance criteria, exact-head tests and independent review pass.

Research may open focused follow-up issues when evidence reveals separate work. Do not manufacture scope.

## Package boundary

tf-build owns reusable infrastructure around Text-Fabric materialization:

- immutable source identity/acquisition;
- safe staging/publication;
- build reports and provenance;
- TF artifact validation/fingerprints;
- reusable Agora host glue;
- generated feature-reference infrastructure;
- low-level graph/writer helpers only when multiple consumers justify them.

tf-build does **not** own:

- corpus parsers or canonical scholarly IRs;
- slot/node ontology decisions;
- source-specific semantic normalization;
- EpiDoc/ORACC/TT/ORAEC/AOxml semantics;
- a replacement for Text-Fabric `CV.walk`/`Fabric.save`;
- a replacement for Text-Fabric-Factory XML/TEI/PageXML conversion.

If an abstraction requires a corpus-specific noun to make sense, it probably belongs in the corpus project.

## Consumer-driven extraction

Before adding shared behavior:

1. identify at least one concrete duplicated implementation;
2. inspect the current consumer contract and tests;
3. prefer two independent consumers before freezing a broad abstraction;
4. migrate consumers incrementally rather than rewriting several repositories at once;
5. preserve behavior with contract tests at the extraction boundary.

Infrastructure primitives with intrinsically generic contracts (for example full immutable Git SHA validation) may begin with one implementation precedent, but their API still needs adversarial edge-case tests.

## Safety and reproducibility

- Never execute downloaded/candidate source code merely to identify or validate it.
- Acquisition may access the network; conversion/materialization helpers should operate on local inputs unless explicitly documented otherwise.
- Reject ambiguous revisions, dirty checkouts and unsafe path states by default.
- Never silently overwrite an existing artifact unless the active contract explicitly provides replacement semantics with stale-output protection.
- Build/release claims must bind to immutable source identity and exact generated artifact evidence.
- Generated reports may carry provenance/diagnostics, but tf-build must never encourage semantic sidecars as a substitute for modelling corpus data in TF.

## Autonomous loop

When no unblocked feature ticket remains, continue with performance, stability, ergonomics, documentation, validation, release engineering and edge cases using the same gate sequence.

Do not leave duplicate or orphaned implementation PRs/branches. One ticket should have at most one canonical active implementation PR.
