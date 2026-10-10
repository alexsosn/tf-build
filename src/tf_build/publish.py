"""Public low-level atomic no-clobber publication of an already-built path.

This API only performs the final filesystem publication. Callers own validation,
private staging, cleanup, and any host-specific existing-empty-output policy.
"""

from __future__ import annotations

from pathlib import Path

from ._atomic import publish_path_no_clobber as _publish_atomic


def publish_path_no_clobber(
    source: str | Path,
    destination: str | Path,
) -> None:
    """Atomically rename a staged file/directory to an *absent* destination.

    Unlike a preflight exists() check plus rename/replace(), this refuses even
    an empty directory or symlink created concurrently at the destination.
    It propagates FileExistsError for an existing target and OSError if atomic
    no-clobber publication is unsupported, or the OS rename otherwise fails.
    It does not create a stage, clean failed stages, validate file contents,
    guarantee fsync durability, or defend against mutable directory ancestors.
    """
    _publish_atomic(Path(source), Path(destination))


__all__ = ["publish_path_no_clobber"]
