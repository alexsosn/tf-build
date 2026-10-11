# Research: Git source roots ending with significant whitespace (#76)

## Source-backed defect

On main `dca00f32bdcd0d36aab2a7192b319a4f4f5aaf89`, `src/tf_build/source.py::_run_git` executes actual Git commands via `subprocess.run(..., text=True)` and returns `result.stdout.strip()`. Its callers include `verify_git_source`'s `rev-parse --show-toplevel`, `rev-parse HEAD^{commit}`, `--is-inside-work-tree`, porcelain status, and ignored-file NUL inventory. Removing **all** leading/trailing whitespace is incompatible with a valid POSIX directory name ending in spaces or a tab. It also rewrites leading whitespace in status output.

I tested a real `git init` in a temporary directory named `repo trailing  `, then ran `git -C <path> rev-parse --show-toplevel`. The command returned the literal absolute path ending with two spaces **followed by one newline**. `stdout.strip()` removed the two path spaces, making `Path(...).exists()` false; removing just the final LF preserved the existing path. No simulated Git output or invented corpus fixture was involved.

Existing `tests/test_source.py::_make_repo` already makes and commits actual Git worktrees, so the regression can rename its committed directory to a trailing-whitespace path and assert that `verify_git_source(..., expected_revision=...)` succeeds. Windows cannot portably create such paths and will skip this regression; CI Linux runs all Python 3.11–3.14 cases.

## Contract / compatibility

Git line-oriented commands in this module delimit their output with a final LF, and `text=True` normalizes CRLF under subprocess decoding. Remove **exactly one final newline** via `.removesuffix("\n")` rather than `.strip()`; do not trim path bytes, accidentally erase whitespace-only path/status content, convert subprocess semantics, or print credential-bearing locator arguments. NUL-delimited `ls-files -z` output intentionally has no LF suffix, so `.removesuffix` leaves it untouched. The existing error sanitization and timeout tests remain authoritative.

This is a narrow bug fix in generic source verification, not a corpus converter or source-acquisition rewrite. It must not cause a versioned release or ORAEC integration.
