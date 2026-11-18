# Plan: researcher TF validation entry point (#120)

1. Add a deterministic subprocess RED test using `examples.tiny_tf_publication.publish_tiny_corpus` as a real native Text-Fabric fixture. Probe default exhaustive reload, selectable validation depth, `--require-otext`, missing warp, and source-byte preservation.
2. Implement `src/tf_build/__main__.py`, mapping argparse options directly to `validate_tf_artifact`; use a consistent machine-readable success object and concise errors. Keep this package-level invocation narrow: one `validate` subcommand.
3. Include the same command in `scripts/check_installed_wheel.py` with a genuine staged/published corpus, ensuring distribution CI proves the entry point exists outside editable checkout.
4. Add quickstart usage to `README.md` with clear limits: `metadata` does not load feature bodies, `selected` does not load every feature, and `all` is exhaustive structural TF reload, not corpus-science certification.
5. Run exact-head `ruff`, strict mypy, Python 3.11–3.14 pytest and distribution smoke CI. Freeze head; inspect final patch and actual smoke results from an independent skeptical perspective, repeat gates if changed, then merge.

No dependency or build-system changes are expected. `python -m` works for a clean wheel using ordinary setuptools package-file inclusion.
