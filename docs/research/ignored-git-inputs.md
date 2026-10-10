# Research: ignored Git files escape "clean" revision verification

Issue #45

## Actual failure and consumer evidence

`src/tf_build/source.py::verify_git_source` currently calls `git status --porcelain=v1 --untracked-files=all --ignore-submodules=none`. This validates tracked/staged changes and *ordinary* untracked files, but Git intentionally does not report ignored files. Real local Git reproduction: commit a `.gitignore` containing `raw/`, then create `raw/input.tsv` without committing. The current status command returns an empty string. `git ls-files --others --ignored --exclude-standard --directory` returns `raw/` even though the ignored corpus bytes are not tied to HEAD.

This matters to actual consumers: `alexsosn/TLHdig-TF/.gitignore` excludes `refs/`, documented there as *external sign lists, read at build time for validation only*. It also ignores `repaired/`, `tf/`, and local build reports. A converter can read those local non-HEAD inputs while claiming the tracked checkout is clean. Strict provenance therefore requires either rejecting ignored local data or tracking a separate immutable identity for it.

## Git root vs subdirectory

Git behavior was tested with a tracked `sub/` subtree and ignored `raw/` plus `.venv/` at the repository root. `git -C repo/sub ls-files --others --ignored --exclude-standard --directory -z` returned empty even though the same command from the repository root returned both ignored dirs. `verify_git_source` permits passing a nested source path, but the opted-in **repository-wide** ignored inventory must run from the resolved Git toplevel, not the caller subdirectory. The existing status check reports changes outside a selected subtree.

## Decision and scope

Add opt-in `reject_ignored_files: bool = False` to `verify_git_source`, validated as a bool before any Git command. In strict mode, after the existing clean status check, execute `git ls-files --others --ignored --exclude-standard --directory --no-empty-directory` using the already resolved `repository_root` and existing per-command timeout. Reject any nonempty listing with `GitSourceError` without echoing paths (ignored names may contain secrets). `--directory` collapses completely ignored trees, avoiding an unnecessary complete filename enumeration for large caches. No new parsing format is needed because this check only needs a nonempty response.

The default must stay False: normal developer checkouts have ignored `.venv/`, `.tf/`, caches and generated outputs. It would be a breaking mistake to change the meaning of *ordinary clean Git status* for all current consumers. For strict release gates callers can opt into the stronger preflight; they still must pin/hash external dependencies and use local, controlled input layouts.

## Limits

This is **not** an atomic checkout snapshot or sufficient reproducibility proof. It does not detect extra data read from outside the repository, external network inputs, files created after verification, modified ignored submodule internals, or ignored files generated during conversion. It does not imply that clean tracked SHA values describe untracked data. Normal `fetch_git_source` remains unchanged, with no additional subprocess or network operation in its default flow.
