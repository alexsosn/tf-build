# Plan: normalize local relative Git paths before staged fetch

Issue #51

1. RED-first tests with real Git 2.x:
   - create real source repo with pinned commit, `monkeypatch.chdir(parent)`, and `fetch_git_source("./repo-sha1", absolute-destination, revision=sha)`. Require exact SHA and actual tracked file in detached clean checkout.
   - repeat with bare `repo-sha1` and `./-repo` path forms.
   - assert missing explicit `./does-not-exist` fails before destination parent creation.
   - record Git fetch argv and assert a normalized absolute local source is placed after `--`, preserving SHA and confidentiality of remote locators.
2. Implement narrow source-locator normalization at the validated `repository` boundary, *before* any destination filesystem mutation. Skip URL/SCP-like locators, preserve absolute paths, resolve only existing local directories and explicit relative path policies.
3. Document working-directory semantics and limits without changing other Git transport policies.
4. Run Ruff, mypy, full real Git pytest and wheel distribution CI on exact PR head Python 3.11–3.14.
5. Obtain independent skeptical review of real Git evidence, command option safety, HTTP/SSH/SCP preservation, staging cleanup and local path resolution. Never merge on stale CI.
