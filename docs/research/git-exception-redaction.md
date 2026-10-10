# Research: credential-bearing Git subprocess errors

Issue: #32; related timeout PR: #31

## Verified concrete failure

`tf_build.source._run_git` receives a repository locator as the final argument to `git remote add origin URL`. Before this issue, the generic `CalledProcessError` / `OSError` branch formats `" ".join(args)` in the top-level `GitSourceError`. This can expose the literal URL username/password or bearer-like token.

The new `TimeoutExpired` branch in #31 uses a safe **top-level** operation-only message but `raise GitSourceError(...) from exc` still preserves an exception containing the original Git argument array. Direct Python 3 local reproduction shows `"SECRET" not in str(error)` but `"SECRET" in "".join(traceback.format_exception(error))` when `TimeoutExpired.cmd` contains the repository locator. This is a concrete chained-traceback leak, not a hypothetical audit preference.

## Error contract

Keep public `GitSourceError` informative by identifying a fixed operation (e.g. `remote`, `fetch`) and the numeric timeout or return code. Never serialize raw command arguments, repository URLs, captured stdout or stderr into its message.

Python's normal exception chaining can retain sensitive `exc.cmd` data. Build a **new sanitized cause** with the same important type/metadata but only `["git", operation]` as `cmd`, and raise the domain error `from` that sanitized cause. A direct `traceback.format_exception` then contains useful exception type/timeout or return code without printing the untrusted URL; Python's implicit context of the original exception is suppressed by the explicit sanitized cause.

For generic process startup `OSError`, omit potentially sensitive argument/path details in the public message and suppress the original context in normal formatted tracebacks. The original error may remain introspectable in-process via `__context__`; this is error-reporting redaction, **not** a claim of secure memory erasure.

## Scope

Only `_run_git` exception reporting, no changed Git command, capture policy, stdout/stderr interpretation, revision pinning, staging cleanup or no-clobber semantics. Do not use simplistic URL regex redaction that misses SCP-style, percent-encoded or custom transport credentials.

No shell interpolation or extra remote network execution.
