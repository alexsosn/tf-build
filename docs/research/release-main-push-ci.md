# Issue #92: release CI must be a main push

## Evidence from actual code

At main SHA `96d5e7e1055446a3e685113d2b5a76443d5675f0`, `.github/workflows/release.yml` checks whether a successful GitHub Actions CI workflow run exists using `head_sha=$TF_RELEASE_SOURCE&event=push&per_page=100`. Its `--jq` predicate selects only matching `head_sha` and `conclusion == "success"`. Neither the API request nor the result filter names `main`.

The GitHub Actions run record has separate `head_branch`, `head_sha`, `event`, and `conclusion` fields. The repository's live Actions listing returned `head_branch: "main"` on main push runs and a separate feature-branch name on PR-triggered runs. The vulnerability here follows directly from the release workflow's omission: a push to some *other branch* at the same SHA can generate a successful run; the release gate would count it as success even if main push CI were missing or red.

The release already verifies tagged ancestry in main, so restricting to the main-branch push is consistent with its stated policy. Its `release` environment approval, manual dispatch, exact tag/version and artifact gates must remain unchanged. The existing `tests/test_release_workflow.py` only verifies existence of the SHA query and a success predicate, not branch identity.

## Scope

Narrow repair: add the GitHub API `branch=main` filter to the exact-SHA push query and require `head_branch == "main"` inside the jq selection. Retain explicit SHA + success checks. A filtering change is needed even if GitHub's branch query is expected to work, so a response containing both main and non-main runs is independently filtered. Keep existing fail-closed `passed < 1` behavior.

## Adversarial cases

1. Same commit SHA, successful push on topic branch, no green main push: reject.
2. Same SHA, green main push: accept as far as this *single* check is concerned.
3. Successful main push but different SHA: reject.
4. PR-event run on main or feature branch: reject.
5. Failure/cancellation on main at exact SHA: reject, unless a separate successful main-push run genuinely exists.

This ticket does **not** publish a release, fetch consumer data, certify wheels, or change ORAEC-TF. Related blockers #60 and #53 remain open.
