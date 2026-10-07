# Plan: cancel superseded CI runs

Issue: #17

## RED

Add a static workflow-contract test that reads `.github/workflows/ci.yml` and requires:

- a top-level `concurrency` section;
- group expression `${{ github.workflow }}-${{ github.ref }}`;
- `cancel-in-progress: true`.

The test must fail on the current workflow.

## Implementation

Add only the three-line top-level concurrency policy after permissions and before jobs. Do not change triggers, permissions, matrix, or quality steps.

## GREEN

Run the full existing quality suite through GitHub Actions on the PR. The PR itself provides an integration check that the edited workflow parses and executes.

## Independent review

Verify:

- group is not global across all PRs;
- workflow name is part of the group;
- PR refs remain isolated from main;
- latest exact-head run is still required;
- no unrelated workflow behavior changed.
