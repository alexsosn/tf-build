# Plan: optional rejection of ignored Git source files

Issue #45

1. RED-first actual Git repository tests: create `.gitignore` committed to HEAD, ignored `raw/input.tsv`, and verify `git status --porcelain` remains clean; assert the ordinary default `verify_git_source` succeeds while opt-in `reject_ignored_files=True` rejects. Once ignored bytes are removed, strict verification must succeed.
2. Use a nested selected source directory while ignored inputs live at the repository root. The strict inventory must detect them **from the resolved Git toplevel**; this catches the subdirectory-scoping bug demonstrated in the research. Do not expose ignored file paths in error strings.
3. RED-first real Git test: an ignored but empty `raw/` directory is listed by `--directory` alone. Include `--no-empty-directory` to reject only ignored data-bearing entries, preserving strict verification for empty ignored placeholders.
4. RED-first Git test for an ignored filename consisting entirely of spaces. Newline-delimited Git output and `_run_git().strip()` currently collapse it to empty, so add `-z` and assert strict verification rejects the real ignored file rather than returning false success.
5. Test invalid `reject_ignored_files` values (`0`, `1`, `"true"`, `None`) fail before Git inspection. Check caller's timeout propagates to extra Git subprocess; keep existing full commit SHA and clean status behavior intact.
6. Implement one optional boolean on `verify_git_source`; do not change `fetch_git_source` or always-on verification behavior. `ls-files --others --ignored --exclude-standard --directory` is read-only/offline, and runs only when strict mode is requested.
7. Document opt-in strictness, performance cost for ignored trees, consumer example (TLHdig refs), and limits of claim. Run exact-head quality on Python 3.11–3.14 and distribution-wheel smoke, then a genuinely independent adversarial review grounded in real local Git output and actual consumer .gitignore.
