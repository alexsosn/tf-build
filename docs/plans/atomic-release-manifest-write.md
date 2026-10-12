# Plan: atomic create-only wheel manifest publication (#86)

1. Land source-backed research and this plan before behavior changes.
2. Add deterministic tests against `scripts.wheel_manifest.write_wheel_manifest` to `tests/test_wheel_manifest.py` on actual temporary filesystem: invalid JSON record, injected fsync failure, competing destination on final publication, exact output and existing destination preserve. Commit tests-only and observe real GitHub Actions RED on old production code (Ruff/mypy clean where possible).
3. Implement narrow code: `json.dumps` first; `tempfile.mkstemp(dir=path.parent,prefix=...)`; `with os.fdopen(fd,"w",encoding="utf-8",newline="\\n")` write+flush and `os.fsync`; `os.link(staging,path)` create-only; finally `os.unlink(staging)`. Ensure fd never leaks if `os.fdopen` raises, and avoid deleting an existing target on any error. Preserve JSON bytes and script API/schema.
4. Freeze final exact head and verify Ruff/mypy, full pytest on Python 3.11–3.14, distribution direct/sdist byte parity, installed wheel and offline wheelhouse smoke + release manifest. Review skeptical patch and actual logs independently, including Windows/link semantics and symlink/competitor races.
5. Mark draft PR ready and squash merge only if all exact-head checks pass and review PASS, then verify post-merge main CI. No release or version tag publication.
