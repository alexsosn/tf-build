# Research: pinned staged Git source acquisition

Issue: #3

## Existing consumer behavior

### ORAEC-TF

`alexsosn/ORAEC-TF/src/oraec_tf/source.py::fetch_source` currently:

- requires a full immutable revision before running Git;
- accepts a nonexistent or pre-existing empty destination;
- rejects symlink, non-directory and non-empty existing destinations;
- creates a staging directory beside the destination;
- initializes Git, adds one origin, shallow-fetches the exact requested commit, and checks out `FETCH_HEAD` detached;
- verifies the staged checkout with the same local verification contract used for existing sources;
- publishes by replacing the destination with the staging directory;
- removes staging state on failure;
- restores a caller-provided empty destination if publication fails after that directory was removed.

This is a strong first implementation precedent, but it is SHA-1-specific because ORAEC pins a 40-character commit.

### CopticScriptorium-TF / Agora boundary

CopticScriptorium-TF deliberately keeps conversion network-free. Its Agora adapter receives already-acquired local input. That remains the preferred materializer boundary: shared Git acquisition is useful for direct/development workflows and acquisition hosts, but corpus conversion must not start fetching implicitly.

## Real Git behavior measured

With Git 2.47.3, local staged acquisition was exercised against both repository object formats:

- SHA-1 source → SHA-1 staging repository → exact shallow fetch succeeds;
- SHA-256 source → SHA-256 staging repository → exact shallow fetch succeeds.

A generic implementation that accepts 64-hex revisions but always runs plain `git init` would initialize SHA-1 storage and therefore cannot honestly promise SHA-256 acquisition. Staging object format must be selected from the validated revision length.

## Destination contract

The create-only default should accept:

1. a destination that does not exist;
2. a caller-created empty physical directory.

It should reject before network/Git acquisition:

- any symlink destination, including dangling symlinks;
- an existing non-directory;
- a non-empty directory.

Staging belongs in the destination parent so final publication can use a same-filesystem rename/replace. This gives an atomic directory-entry publication on ordinary local filesystems; it does not make the entire build transaction durable against filesystem or power failure.

If the caller supplied an empty destination, a failed acquisition must leave that empty directory in place. If the destination did not exist, failure must not leave it behind.

## Repository identifier

The acquisition API accepts an opaque Git repository locator string (URL or local path) and passes it as one subprocess argument; it does not use a shell.

This layer does not claim that the repository locator is authoritative provenance, does not compare remotes after checkout, and does not execute source-tree code.

## Security boundary

- revision is validated before any Git/network operation;
- conversion is not invoked;
- no shell interpolation is used;
- candidate source code is never executed;
- transport/network trust remains Git/host policy and is not rebranded as a sandbox guarantee.

## Non-goals

- branch/tag resolution;
- GitHub-specific API acquisition;
- archive/Zenodo downloads;
- repository ownership/authenticity proof;
- automatic conversion after acquisition;
- replacement of existing non-empty source trees.
