"""Safe staging workspace for create-only artifact publication."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from types import TracebackType
from typing import Literal

from ._atomic import publish_path_no_clobber


class BuildWorkspaceError(RuntimeError):
    """Raised when a build workspace is used outside its valid lifecycle."""


class BuildWorkspace:
    """Stage a complete artifact privately and publish it without clobbering."""

    def __init__(self, destination: str | Path) -> None:
        requested = Path(destination)
        if not requested.name or requested.name in {".", ".."}:
            raise BuildWorkspaceError(
                f"destination must name an artifact path: {requested}"
            )
        if requested.is_symlink() or requested.exists():
            raise FileExistsError(f"destination already exists: {requested}")

        try:
            requested.parent.mkdir(parents=True, exist_ok=True)
            parent = requested.parent.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise BuildWorkspaceError(
                f"could not prepare destination parent: {requested.parent}"
            ) from exc

        canonical = parent / requested.name
        if canonical.is_symlink() or canonical.exists():
            raise FileExistsError(f"destination already exists: {canonical}")

        self._destination = canonical
        self._staging: Path | None = None
        self._state: Literal["new", "active", "published", "closed"] = "new"

    @property
    def destination(self) -> Path:
        """Canonical final artifact path."""
        return self._destination

    @property
    def path(self) -> Path:
        """Active private staging directory."""
        if self._state != "active" or self._staging is None:
            raise BuildWorkspaceError("build workspace is not active")
        return self._staging

    def __enter__(self) -> BuildWorkspace:
        if self._state != "new":
            raise BuildWorkspaceError("build workspace can only be entered once")
        if self._destination.is_symlink() or self._destination.exists():
            raise FileExistsError(
                f"destination already exists: {self._destination}"
            )

        try:
            self._staging = Path(
                tempfile.mkdtemp(
                    prefix=f".{self._destination.name}.tf-build-",
                    dir=self._destination.parent,
                )
            )
        except OSError as exc:
            raise BuildWorkspaceError(
                f"could not create build staging directory beside {self._destination}"
            ) from exc

        self._state = "active"
        return self

    def publish(self) -> Path:
        """Atomically publish the staged artifact without replacing a target."""
        if self._state != "active" or self._staging is None:
            raise BuildWorkspaceError("build workspace is not active")

        staging = self._staging
        publish_path_no_clobber(staging, self._destination)
        self._staging = None
        self._state = "published"
        return self._destination

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        cleanup_error: OSError | None = None
        staging = self._staging
        if self._state == "active" and staging is not None:
            try:
                shutil.rmtree(staging)
            except OSError as error:
                cleanup_error = error

        self._staging = None
        self._state = "closed"

        if cleanup_error is None:
            return
        if exc is not None:
            exc.add_note(
                f"tf-build staging cleanup failed for {staging}: {cleanup_error}"
            )
            return
        raise BuildWorkspaceError(
            f"build staging cleanup failed for unpublished directory: {staging}"
        ) from cleanup_error


__all__ = ["BuildWorkspace", "BuildWorkspaceError"]
