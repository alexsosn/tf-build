# Research: Git fetch locator must not be parsed as an option

Issue #49

## Real source and Git CLI evidence

`src/tf_build/source.py::fetch_git_source` calls `_run_git(staging, "fetch", "--depth", "1", repository, requested_revision)`. It rejects only empty/whitespace locators. Passing an argument list to subprocess avoids shell parsing, but **Git still parses dash-leading argv as its own options**.

Executed Git 2.47.3 against a fresh local `git init`:

- `git fetch --depth 1 --definitely-not-a-repository <40-hex>` returned exit 129 and `unknown option 'definitely-not-a-repository'`, proving `repository` became an option instead of a remote.
- `git fetch --depth 1 -- --definitely-not-a-repository <40-hex>` returned exit 128 with Git's pathname refusal, **not** an option parse; `--` separates flags and positional args.
- A real local source `git init; git commit` and `git fetch --depth 1 -- /tmp/src <full SHA>` returned success. `--` thus preserves our supported pinned-SHA local fetch path.

NUL is invalid in `subprocess.run` arguments; CR/LF/TAB are not acceptable in an opaque source locator's stable public API and can obscure error reporting. Unlike persisted `GitSourceProvenance`, this acquisition input may legitimately contain private authentication info; don't echo it in the reject error.

## Decision and non-goals

Before touching destination or spawning any Git process: reject repository arguments starting with `-`, all ASCII controls (C0 and DEL), empty or whitespace-only text. Keep arbitrary valid HTTPS, SSH, SCP and local-path locators otherwise accepted. Add `--` as an explicit end-of-options argument to the Git fetch command as defense in depth. Caller can express an unusual local path starting with a dash as `./-path` if appropriate.

Do not change Git's credential, timeout, exact full-SHA, source snapshot or no-clobber contracts. Do not build a generalized Git URL parser, execute a shell, or rewrite user-supplied locator text.
