# Plan: hash-addressable wheel CI artifact and offline wheelhouse smoke

Issue #58.

1. RED-first tests of `scripts/wheel_manifest.py`: generate small *real ZIP archives* carrying `tf_build-*.dist-info/METADATA`, and assert SHA256 of exact bytes, canonical full SHA-1/64-hex source revision, metadata/package/version consistency, deterministic serialization and exclusive creation. Reject missing/multiple/corrupt wheels, wrong names/versions and invalid revisions without emitting an output.
2. Production generator reads project metadata using Python 3.11 stdlib `tomllib` and wheel embedded `METADATA` with stdlib `email.parser`. Do not import/execute built wheel code, and do not trust the external filename without comparing its embedded metadata.
3. In distribution CI, checkout the literal PR head SHA on PRs; keep editable-project vs noneditable wheel RED/GREEN smoke. Generate source/digest manifest for exactly one built project wheel. Build a local wheelhouse with all runtime dependencies while network is available; install from `--no-index --find-links` in a fresh venv and rerun wheel import smoke outside checkout.
4. Emit SHA256 inventory of the full resolved wheelhouse and upload wheel, manifest and wheelhouse with limited retention via read-only `actions/upload-artifact`. Document that the dependency set is **not lockfile-frozen** between runs, and the artifact is ephemeral.
5. Require exact-head Python 3.11–3.14 Ruff, strict mypy and pytest plus completed distribution test; independently review wheel contents, metadata and actual distribution logs. Do not claim release completion.
