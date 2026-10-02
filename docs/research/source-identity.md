# Research: immutable Git source identity and local verification

Issue: #2

## Consumers inspected

### ORAEC-TF

`alexsosn/ORAEC-TF/src/oraec_tf/source.py` currently:

- accepts exactly 40 hexadecimal characters;
- normalizes revisions to lowercase;
- resolves `HEAD` with local `git rev-parse HEAD`;
- rejects a mismatch against an expected revision;
- rejects dirty tracked and untracked state via `git status --porcelain --untracked-files=all`;
- returns a frozen `SourceSnapshot(path, revision)`;
- wraps Git execution failures in a source-specific exception.

Its tests use real temporary Git repositories for verification and use mocks only for acquisition command sequencing.

### CopticScriptorium-TF

`alexsosn/CopticScriptorium-TF/copticscriptorium_tf/converter.py` currently validates provenance identifiers as either:

- a full 40-hex Git object id;
- a full 64-hex Git object id;
- the explicit corpus-specific sentinel `unversioned-local`.

The sentinel belongs to a consumer workflow and must not become a generic Git checkout identity. The useful shared evidence is that a reusable Git identity validator should not hard-code SHA-1 only.

### Local Git behavior measured for this research

With Git 2.47.3:

- an ordinary repository produced a 40-character SHA-1 commit id;
- `git init --object-format=sha256` produced a 64-character SHA-256 commit id;
- `git rev-parse HEAD` works from a subdirectory and resolves the repository commit;
- `git rev-parse --show-toplevel` identifies the checkout root.

## Contract decisions

### Full object ids

The generic lexical validator will accept exactly 40 or 64 hexadecimal characters and normalize to lowercase.

This deliberately rejects branch names, tags, `HEAD`, abbreviations and consumer-specific sentinels. A caller that supports an unversioned local source must model that outside the Git snapshot API.

### Checkout scope

Verification accepts a directory inside a non-bare Git working tree, not only the top-level directory. The returned snapshot records both:

- the canonical caller-selected `path`;
- the canonical Git `repository_root`.

Cleanliness is checked for the whole working tree. This is conservative: a dirty sibling outside a selected source subdirectory still invalidates a reproducible Git snapshot.

### Cleanliness

Tracked, staged, untracked and submodule dirtiness are failures. Ignored files remain ignored, matching normal Git reproducibility expectations and the ORAEC precedent.

Use porcelain output for machine-readable detection; do not parse human `git status` text.

### Object format

The snapshot records `sha1` or `sha256`, derived from the validated resolved commit length. No broader hash format is advertised until Git and a real consumer require it.

### Network boundary

Verification invokes only local Git inspection commands. It must not fetch, contact remotes, or prove that an origin URL owns the commit. Acquisition is a separate ticket (#3).

### Error boundary

Expose a package-level `GitSourceError` with actionable high-level messages. Preserve the original subprocess exception as `__cause__`, but do not include arbitrary command stderr in the public message by default.

## Non-goals

- remote/origin identity validation;
- fetching/cloning;
- archive identities;
- consumer-specific `unversioned-local` sentinels;
- deciding source licensing or scholarly validity.
