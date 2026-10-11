"""Public low-level atomic no-clobber path publication.

Callers own staging, validation, destination lifecycle and error cleanup.
This module exposes the same platform-specific primitive used by BuildWorkspace:
one atomic rename that refuses to replace an already existing destination.
It neither validates artifact contents nor offers replacement semantics.
"""

from __future__ import annotations

from ._atomic import publish_path_no_clobber

__all__ = ["publish_path_no_clobber"]
