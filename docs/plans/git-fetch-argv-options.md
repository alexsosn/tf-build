# Plan: fail closed on Git fetch locator option parsing

Issue #49

1. RED-first tests added before production:
   - `--upload-pack=evil`, `--all`, `-q`, embedded NUL, newline, TAB and DEL must raise `GitSourceError` before destination or parent creation.
   - Use a literal sentinel URL string in one rejected case and assert error messages do not echo caller input.
   - Positive local real Git fixture `fetch_git_source` must preserve exact pinned SHA and clean detached checkout.
2. Implement one narrow input check before `Path(destination)` work and `--` end-of-options separator in Git fetch argv, retaining its existing timeout parameter.
3. Update README to describe locator preflight and no shell/option injection guarantee. Explicitly do not claim that Git transport or local environment is a security sandbox.
4. Full quality matrix Python 3.11–3.14, distribution wheel smoke, and genuinely independent adversarial review of actual subprocess argument arrays and local Git data. Review after code freeze on the same exact SHA.
