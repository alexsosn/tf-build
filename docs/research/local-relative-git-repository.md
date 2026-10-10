# Research: caller-local relative Git paths change meaning under git -C

Issue: #51

## Concrete executable evidence

Git 2.47.3 reproduction in a real local temporary repo:

1. From the parent of `./upstream`, create a Git repository and commit a file. Record the exact 40-hex HEAD.
2. Initialize a separate `./stage` directory.
3. `git -C /tmp/.../stage fetch --depth 1 -- ./upstream SHA` exits 128: `fatal: './upstream' does not appear to be a git repository`.
4. Replace the relative repo argument with the absolute `/tmp/.../upstream`; the same fetch succeeds.

The issue is not shell injection (the helper uses `subprocess.run(argv)`) or option parsing (issue #49 already added end-of-options `--`). Git changes its working directory to the staging directory before resolving a local repository path.

## API decision

Treat an existing *local relative directory* as a caller-local source, resolve to an absolute filesystem path **before staging and Git execution**. This includes `./repo`, `../repo`, `repo`, and `./-repo`. A missing explicit `./` or `../` path is an early `GitSourceError` with a generic message. An unrecognized relative bare locator remains a Git locator, preserving remote-name semantics. Already-absolute filesystem paths are unchanged.

Never apply local-path resolution to URI-like URLs containing `://`, or SCP-style Git transport locators like `git@host:org/repo.git`; Git authentication and network behavior remain its own. An existing actual filesystem directory wins over ambiguous *bare* local names, matching user intent for local sources; this decision is subject to caller current-working-directory semantics.

## Safety/compatibility boundary

- Preserve revision validation, timeout, no-clobber staging, no transient fetch URL persistence, complete `verify_git_source` checks and source digest semantics.
- Validate option-like and control-containing locators **before** filesystem probing. Do not log caller-provided repository string, which may embed credentials.
- Local path normalization does not verify a source is Git before fetch; Git still verifies the exact commit and detached state. No source code execution.
- No generic Git URL parser or shell usage. Don't resolve arbitrary non-local remote locators using filesystem existence checks.
