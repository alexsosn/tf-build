# Plan: expose an atomic no-clobber path publisher

Issue: #54.

1. **RED-first:** commit tests importing `tf_build.publication.publish_path_no_clobber` before that module exists. They must use real temporary directories: success moves bytes; empty competing directory keeps the same inode and contents; nonempty/file/symlink destinations remain untouched; missing source errors do not create a target. Test fails on original code due missing public module, not a mocked rename.
2. Implement a tiny public module exporting the exact existing `tf_build._atomic.publish_path_no_clobber` function, with an accurate docstring and `__all__`. No duplicated platform-specific logic and no behavior change to `BuildWorkspace`.
3. Document both distinct lifecycles: BuildWorkspace manages staging for initially absent destinations; the low-level public function lets a caller manage an existing host-owned empty destination and validates neither artifact nor lifecycle.
4. Run full Python 3.11/3.12/3.13/3.14 CI including Ruff, strict mypy, pytest and installed-wheel smoke on the **exact PR head**. Independent adversarial review must examine actual kernel collision and inode-preservation evidence, and test the compiled wheel's public import.
5. Leave ORAEC's active PR #58 untouched; coordinate an import migration after its independent CI/review gate. No other new broad API.
