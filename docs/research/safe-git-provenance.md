# Research: portable Git provenance must not contain access credentials

Issue #35

## Current production contract

`src/tf_build/report.py::GitSourceProvenance` preserves a caller-declared repository locator verbatim in `BuildReport.to_dict()` and `to_json()`. Existing `_validate_repository_locator` prohibits local absolute/home paths, traversal and `file:` but accepts any otherwise nonblank URL, including `https://user:TOKEN@server/repo.git` or `https://server/repo.git?access_token=TOKEN`. Those strings become exported operational report fields that might be shared publicly.

`tf_build.source.fetch_git_source` is deliberately separate: it can use a credential-bearing URL for network access. The **report** should instead identify the same repository by its clean public locator.

## Grounded locator forms

Existing tests accept `example/upstream`, `https://github.com/example/upstream.git`, `ssh://git@example.org/example/upstream.git`, and the SCP-style `git@example.org:example/upstream.git`. Username `git` is conventional for SSH key transport and not a password. In contrast, HTTP(S) authority userinfo may be a bearer token even without a colon. URI query/fragment components are unnecessary to identify the repo and may hold private tokens.

## Decision

For schemes of the form `scheme://authority/path`, reject any query or fragment; reject `password` in userinfo regardless of scheme; and reject **all** HTTP(S) authority userinfo, including username-only. Preserve SSH username-only locators (`ssh://git@host/path`) but disallow passwords. For SCP syntax, retain `git@host:path` without query/fragment. Reject `?` and `#` in non-URL locator strings. Treat malformed URL parsing as a validation failure.

Do not try partial token masking or secretly rewrite a user-supplied locator; callers should pass a separately sanitized provenance repository field. An SSH username can theoretically be an access token and credentials can be embedded in arbitrary opaque path segments, so this is a bounded policy, **not** a general secret detector.

## Compatibility

Existing clean repository locators and SHA-1/SHA-256 revisions remain accepted. Only source locators inappropriate for portable reporting fail at model construction. Do not change fetch_git_source's network/credential policies.
