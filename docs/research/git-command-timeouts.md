# Research: bound Git subprocess waits in source acquisition

Issue: #30

## Real production code and effects

`src/tf_build/source.py::_run_git()` runs `subprocess.run(["git", "-C", source, ...], check=True, capture_output=True, text=True)` with no `timeout`. `fetch_git_source` executes init, remote add, fetch of the exact 40/64-hex commit, checkout and verification **while a temporary sibling staging directory exists**. `verify_git_source` executes four Git inspection commands including `status --porcelain --ignore-submodules=none`.

On an unresponsive transport, filter, lock, or filesystem, the direct Git subprocess can stay blocked indefinitely, leaving a pending staging tree and a materialization task unable to finish.

Python stdlib [subprocess.run](https://docs.python.org/3/library/subprocess.html#subprocess.run) accepts a per-invocation `timeout`; on `TimeoutExpired`, Python kills and waits for the **direct** child, then raises. It does not promise cancellation of arbitrary transport subprocess grandchildren or a whole-build deadline. The `subprocess.run` creation stage itself may not be interruptible on all platforms.

Git `GIT_TERMINAL_PROMPT=0` can prevent some terminal credential prompts, but is not equivalent to a network/command timeout; changing Git environment/interactive authentication is not necessary for this minimal fix.

## Decision

Introduce `timeout_seconds: float = 1800.0` (30 minutes **per Git command**) on the public acquisition and verification entrypoints, validated as positive finite real seconds before side effects. Pass the bound to **every** `_run_git` call, including nested verification inside acquisition. When `TimeoutExpired` occurs, raise a contextual `GitSourceError`, preserving the cause and existing cleanup. Avoid including remote URL or stderr contents in the timeout message (they could reveal credentials).

30 minutes is a deliberately generous default for large source repositories, with explicit user overrides for slower transports. Existing revision pinning, staged no-clobber publication and dirty working-tree rejection remain unchanged.

## Limits

A per-command timeout is not a global time budget; repeated commands can each consume their allowance. No general subprocess supervision, process-group cleanup or cancellation of Git grandchildren is promised. For truly untrusted remote locators, callers must enforce their own network and credential policy.
