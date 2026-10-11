# Plan: preserve Git stdout except transport newline (#76)

1. Document real POSIX Git path reproduction and all `_run_git` callers before production changes.
2. Commit RED-only tests using the real `_make_repo` helper, rename clean committed worktree to roots ending in ASCII space(s) and tab, and assert exact `SourceSnapshot.path` / `repository_root` plus revision. `skipif(os.name == "nt")`; no mock Git output. Observe failing tests on unmodified source before implementing.
3. Replace global `result.stdout.strip()` with removal of one final Git LF. Do not modify exception sanitization, argument handling, source paths or SHA validation.
4. Run exact-head full Ruff/mypy/pytest Python 3.11–3.14 and genuine distribution jobs. Recheck ignored-file `-z` and porcelain output tests.
5. Independently review frozen head from adversarial perspective (NUL output, meaningful leading/trailing spaces, handling Git status, Windows line-ending universal translation); post a COMMENT review tied to exact SHA, and merge only after all jobs green. Parent release #60 and consumer #53 remain blocked.
