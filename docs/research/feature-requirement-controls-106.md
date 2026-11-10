# TF feature requirement identifiers: ASCII controls (#106)

## Research (2026-11-10, committed before tests and implementation)

- The public `FeatureRequirement` dataclass in `src/tf_build/validate.py` promises a "safe TF filename stem." Its `__post_init__` rejects `""`, `.`, `..`, slash/backslash and whitespace, but checks only `char.isspace()`; it permits NUL, BEL, ESC and DEL. These are not portable feature filename characters. A required feature can therefore be accepted at the contract-construction boundary and fail much later (or fail ambiguously) during artifact validation.
- The existing `tests/test_validate.py::test_invalid_feature_requirement_name_rejected` covers common names but no control characters. Current TF fixtures in that file are genuine outputs of `tf.fabric.Fabric.save` with feature stems `text`, `count`, `relation`, `otype`, etc. These and existing metadata/selected/all validation behavior must stay unchanged.
- `src/tf_build/feature_docs.py::_valid_name` uses a separate tighter expression for generated-reference filenames; it is **not** evidence to impose that expression on `FeatureRequirement`, as broadening/narrowing supported TF names beyond control rejection would change public behavior.
- The current `tf_build.report.ArtifactSummary` path rule, and the newly merged Agora output path rule, both reject Unicode code points 0..31 and 127. Aligning that narrow invariant improves error locality without a shared path/feature abstraction.
- No evidence justifies modifying TF data semantics, rewriting names, replacing upstream Text-Fabric validation or migrating consumers in this ticket.

## Plan and acceptance

1. RED first: add tests for all 33 controls (C0 and DEL) passed directly to `FeatureRequirement`. Check immediate `ValueError` and that the error does not include supplied control-bearing text. Include a positive Unicode name and preserve the existing invalid-name tests. Observe failure on the original code before implementation.
2. GREEN: add a single `any(ord(char) < 32 or ord(char) == 127 for char in self.name)` predicate to the existing validation conditional; keep the established `ValueError` text and all existing lexical allowances.
3. Run exact-head Ruff, mypy, pytest on 3.11–3.14, distribution's direct/sdist-rebuilt/offline installed-wheel real TF publication smoke and producer coverage. Verify source/head stability.
4. Review independently: re-read final diff, actual tests and CI logs; probe escape/ASCII/non-ASCII edge cases and public API compatibility. Merge only if all gates pass.

## Boundaries

This checks the caller-supplied *required* feature name only. It does not certify a TF feature, check the metadata name's correctness, forbid Unicode names, scan corpus bodies, change artifact publication or authorize any new release.
