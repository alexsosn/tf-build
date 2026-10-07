# Research: superseded CI run cancellation

Issue: #17

## Observed repository behavior

PR #16 accumulated 13 workflow runs on one branch while the autonomous review/fix loop advanced through multiple heads. Older queued runs continued consuming matrix capacity even though only the newest head could satisfy the merge gate.

The current workflow triggers on `push: main` and `pull_request`, but has no top-level `concurrency` policy.

## GitHub Actions semantics

GitHub Actions supports workflow/job concurrency groups. A concurrency group permits at most one running and one pending run; a newer pending run supersedes the older pending run. With `cancel-in-progress: true`, an older running run in the same group is also cancelled.

GitHub recommends including the workflow identity in the group so runs from different workflows do not cancel one another.

For this workflow, `github.ref` separates pull-request merge refs from `refs/heads/main`, while `github.workflow` scopes cancellation to CI itself.

Reference:
https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency

## Decision

Add top-level:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

This keeps unrelated PRs independent, cancels obsolete runs for the same PR ref, and lets newer main pushes supersede older main CI runs.

The merge policy remains unchanged: only the latest exact-head CI result is valid.

## Non-goals

- cancelling runs across unrelated PRs;
- changing the Python matrix;
- weakening exact-head CI requirements;
- changing branch protection or merge policy.
