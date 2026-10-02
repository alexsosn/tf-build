# Autonomous development loop

## 1. Select work

Choose the highest-priority unblocked issue. Read the issue, linked research/design, open PRs and recent related changes. Do not start a duplicate implementation.

## 2. Research

Inspect actual current code, consumer repositories, upstream Text-Fabric/Text-Fabric-Factory behavior, and Agora contracts relevant to the issue.

Research should answer:

- which concrete consumers need the behavior;
- what invariants are actually shared;
- what differs and must remain consumer-local;
- failure and security boundaries;
- backward-compatibility/migration consequences;
- how correctness can be tested independently of the implementation.

Persist durable findings in `research.md` or a focused `docs/research/` document. Research may create separate issues when evidence reveals independent work.

## 3. Plan/design

Before production code, define:

- public/internal API;
- invariants and failure policy;
- compatibility constraints;
- consumer migration path;
- test strategy;
- non-goals.

Broad API changes require an update to `design.md` or an ADR/focused design document.

## 4. RED-first TDD

For testable behavior:

1. add a deterministic test against the intended production API;
2. run it before implementation;
3. preserve the observed RED result in the PR/development record;
4. implement the smallest correct behavior;
5. run the focused test to GREEN;
6. run the complete affected suite.

Tests should probe real boundary behavior. Avoid mocks that merely restate implementation logic.

## 5. Integration gates

Use risk-appropriate evidence:

- filesystem/source helpers: real temporary Git repositories and adversarial path cases;
- TF artifact helpers: generate/load actual tiny TF datasets with the supported Text-Fabric version;
- compatibility extraction: run contract tests derived from the consumer repository;
- Agora helpers: exercise the current materializer schema/host boundary without giving conversion network access;
- release work: exact package build/install plus supported Python matrix.

## 6. Freeze exact head

Record the commit under review and run all relevant tests/lint/type checks on that exact head. Production changes after this point require re-running the affected gates.

## 7. Logically independent adversarial review

Review the exact final head from a fresh skeptical perspective. Re-derive likely failure modes from the issue and real consumer behavior instead of validating the implementer's explanation.

Attack questions include:

- Did the abstraction accidentally encode one corpus's semantics?
- Is a permissive path/revision rule weakening an existing consumer invariant?
- Can symlinks, dirty state, partial writes or stale files produce a false-success build?
- Is provenance immutable and sufficient to reproduce the claim?
- Do tests prove the production path rather than a test double?
- Does the abstraction duplicate functionality already owned by Text-Fabric or Text-Fabric-Factory?
- Will migrating a second consumer reveal hidden assumptions?
- Do docs promise more compatibility than the code establishes?

Any behavior-changing fix invalidates the old review and requires re-review of the new head.

## 8. Merge and continue

Merge only after the exact head is green and independently reviewed. Close the issue, reconcile the backlog and take the next unblocked item.

If the feature backlog is empty or blocked, continue performance, stability, ergonomics, documentation, validation, release engineering and edge cases under the same loop.
