# Research: Git acquisition persists source URL credentials

Issue #38

## Reproduced with real Git

Current `tf_build.source.fetch_git_source` initializes a private checkout, executes `git remote add origin REPOSITORY`, then `git fetch --depth 1 origin SHA`, and finally publishes the whole `.git` directory. Git persists `REPOSITORY` literally in `.git/config` as `remote.origin.url`; a URL such as `https://alice:MY_SECRET_TOKEN@testing.invalid/repo` consequently ships the secret with a successful, apparently clean snapshot. This is not fixed by #31's safe error formatting or #35's safe build report identifier.

Reproduced with actual Git 2.47.3 **offline**, setting `GIT_CONFIG_GLOBAL` to a private file with `[url "<localrepo>"] insteadOf = https://alice:MY_SECRET_TOKEN@testing.invalid/repo`. Fetch through `origin` succeeded, but `.git/config` retained the token.

Second real Git experiment confirms `git fetch --depth 1 https://alice:MY_SECRET_TOKEN@testing.invalid/repo SHA` works with the same `insteadOf` rewrite without creating `remote.origin.url` in local config. Git still creates `.git/FETCH_HEAD` recording fetch history; depending on transport/config this can include the original URL and should not be retained in a published checkout.

## Design

1. Do not invoke `git remote add origin`. Fetch the immutable 40/64-hex revision directly from the caller's repository URL. This retains exact SHA pinning and offline local source support without a persistent remote.
2. Checkout `FETCH_HEAD` as detached HEAD as before; then **unlink** `.git/FETCH_HEAD` before the clean-tree verification and publication. The HEAD revision remains a normal Git commit object, so `verify_git_source` and consumers do not need FETCH_HEAD.
3. If fetching, checkout or metadata cleanup fails, private staging is removed by the existing exception path; the destination remains absent or the preexisting empty destination untouched.
4. For the test, install a scoped temporary Git global config using pytest monkeypatch environment and a Git URL rewrite to an actual local repository, proving both successful exact acquisition and no token in shipped textual Git metadata. No external network.

## Limits

This removes known persistent locator stores used by this exact command sequence. It cannot guarantee security if Git transport helpers, credential helpers, user-configured hooks, or other external processes persist secrets elsewhere; it does not zero secret arguments from the invoking Python process or prevent exposure to process listing. A private source snapshot still contains Git internals and may be subject to the caller's broader network/credential policy.
