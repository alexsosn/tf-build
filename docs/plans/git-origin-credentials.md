# Plan: remove persistent Git source acquisition locator

Issue #38

1. RED-first regression built from actual local Git repository and `GIT_CONFIG_GLOBAL` scoped `url.<local-source>.insteadOf` rewrite for a credential-bearing HTTPS URL. Exercise `fetch_git_source` with the URL, exact local SHA, and fresh target. Assert clean detached commit, no origin remote configured, `.git/config` no token, no `.git/FETCH_HEAD` left and no credential in normal Git control text.
2. Implement the smallest change in source.py: remove `remote add`, fetch directly by `repository`, detach checkout from FETCH_HEAD, remove it before verifying and publishing. Leave timeout/error sanitization from #31 unchanged.
3. Preserve all existing local SHA-1/SHA-256, failure-stage cleanup, no-clobber and safe error tests. Where a test explicitly simulates remote-add failure, replace with a meaningful equivalent Git-fetch failure or retain separate error-branch unit coverage; do not delete the credential exception-chain regression.
4. Document that publication retains no raw acquisition remote URL or temporary FETCH_HEAD, without claiming secure deletion of all Git helper state.
5. Run Ruff, mypy and actual Git tests on Python 3.11–3.14 exact head, followed by a fresh adversarial review of the real fixture and inspected published tree.
