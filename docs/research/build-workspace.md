# Research: safe build workspace and create-only artifact publication

Issue: #4

## Consumer evidence

### CopticScriptorium-TF

The current native TF writer already demonstrates a robust create-only pattern:

1. reject an existing final destination;
2. create a sibling `TemporaryDirectory`;
3. serialize the complete TF artifact into staging;
4. validate mandatory output files;
5. publish with an atomic no-clobber filesystem primitive.

Its writer integration tests explicitly verify that a competing empty directory or file is not replaced. The destination inode/content remains unchanged and staging remains available to the caller when the low-level publication attempt fails.

### ORAEC-TF / Git acquisition

ORAEC-TF's source acquisition also stages beside the destination and cleans failed partial state. Its current contract accepts a pre-existing empty destination because the caller may reserve an acquisition directory.

That behavior is useful for source acquisition, but it is not a good default for generated artifacts: accepting and removing a caller-created directory weakens ownership boundaries and creates extra race/restore semantics.

### TLHdig-TF

TLHdig-TF research identified a separate stale-output defect in in-place rebuilds: Text-Fabric 13.1 `Fabric.save(overwrite=True)` overwrites features emitted by the current run but does not remove unrelated obsolete `.tf` files already present in the destination.

A fresh empty staging directory eliminates that stale-feature class for create-only builds. Replacing an existing converter-owned artifact at the same logical path is a separate problem with different crash/availability semantics and is tracked in #14.

## Conclusions

### Default workspace is create-only

The first shared workspace API should require the final destination to be absent. Existing empty directories, files, symlinks and dangling symlinks fail before staging begins.

This is stricter than Git acquisition on purpose. A generated artifact has no reason to borrow ownership of an already-existing final path.

### Complete staging, explicit publication

The workspace exposes one fresh staging directory. Consumers build and validate entirely inside it. Publication occurs only through an explicit `publish()` call.

Context-manager exit must never auto-publish. If parsing, conversion or validation raises, or the caller simply omits `publish()`, staging is removed and the final destination remains absent.

### Atomic no-clobber publication

The #3 adversarial-review sub-loop demonstrated that preflight plus `Path.replace` is racy. Publication must use the private atomic no-clobber primitive introduced there:

- Linux: `renameat2(RENAME_NOREPLACE)`;
- macOS: `renamex_np(RENAME_EXCL)`;
- Windows: rename semantics that fail when destination exists;
- unsupported platforms: fail closed.

A destination created after workspace construction must be preserved.

### Parent path and filesystem boundary

Staging must be created in the physical resolved destination parent. This gives source and destination the same directory/filesystem for the final rename and freezes the path used after any lexical ancestor symlinks have been resolved.

The package does not claim to be a hostile-filesystem sandbox: an attacker able to replace ancestor directories or mount points concurrently is outside this first contract. Agora/sandbox hosts own stronger filesystem isolation.

### No replacement flag

Do not add `overwrite=True`, `replace=True` or an equivalent escape hatch. Safe replacement of a known converter-owned existing tree is tracked separately in #14.

## Non-goals

- TF-specific validation;
- atomic replacement of an existing artifact;
- rollback to an old artifact;
- arbitrary filesystem sandboxing;
- source acquisition;
- automatic publishing on successful context exit.
