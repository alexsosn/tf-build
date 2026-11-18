# Product goals — tf-build

## Users and purpose

Maintainers of independent Text-Fabric converters should be able to reuse a small set of proven build, source-acquisition, validation and publication primitives so that they can focus engineering effort on source semantics and researcher-facing corpus functionality.

## Representative downstream journeys

1. A corpus converter verifies or explicitly acquires an immutable allowed Git source, without leaking credentials into provenance.
2. A converter builds into a safe temporary workspace and publishes a validated native TF output atomically without overwriting an existing user's data.
3. A maintainer runs installed-wheel/native-TF validation with actionable errors rather than rebuilding the same validation code in each corpus repo.
4. A converter emits lightweight truthful build/provenance reports that do not claim scholarly certification.
5. A separate consumer such as ORAEC-TF, IIP-TF, CopticScriptorium-TF or CATSS-TF adopts a shared primitive, removes duplicative local code and passes its own genuine conversion E2E.

## Minimum usable release

The package is installable from an actual immutable distribution and the supported primitives work from a clean installed consumer environment, not only a source checkout. Validate success and failure with at least one real downstream converter, plus the existing producer-specific regression gates. The next concrete delivery is the reviewed 0.1.0rc2 publication (issue #122) and verified consumer adoption, not indefinite changes to publishing infrastructure.

## Scope boundary

Own generic Git source identity, safe staging/publication, artifact checks and truthful operational reports **only when demonstrably shared by real consumers**. Never own a corpus-specific parser, Text-Fabric schema, editorial interpretation, crosswalk, source licence decision or generic XML/TEI conversion framework. Text-Fabric remains the core writer/loader.

## Rules for expanding the library

Require evidence from at least two real consumers before introducing a generic abstraction unless one consumer exposes a concrete cross-project correctness flaw. Prefer extending a current function to a new framework. Stop when downstream maintainers can complete their actual release workflows.

## Autonomous-development decision rules

- Select work by the researcher journeys above, not issue count or the ease of adding tests. Prefer finishing active PRs and releases over opening new tickets.
- Before introducing a new adapter, workflow, registry, protocol, or validation layer, demonstrate that an existing mechanism cannot meet a concrete acceptance need.
- Preserve source fidelity, access controls, security, and applicable upstream rights. Do not invent inferred text or silently weaken correctness gates.
- Batch repetitive data changes and reuse parameterized tests. Keep independent adversarial review proportional to risk, and validate the actual researcher path.
- If two successive cycles do not advance a journey or remove an observed blocker, reconsider the approach. Stop when the scoped deliverable works instead of generating optional infrastructure work.
