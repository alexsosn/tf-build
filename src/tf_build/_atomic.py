"""Internal atomic no-clobber filesystem publication primitives."""

from __future__ import annotations

import ctypes
import errno
import os
import sys
from pathlib import Path

_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
_RENAME_EXCL = 0x00000004


def _raise_publish_error(error_number: int, destination: Path) -> None:
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(
            error_number,
            os.strerror(error_number),
            str(destination),
        )

    unsupported = {
        errno.ENOSYS,
        errno.EINVAL,
        getattr(errno, "ENOTSUP", errno.EINVAL),
        getattr(errno, "EOPNOTSUPP", errno.EINVAL),
    }
    if error_number in unsupported:
        raise OSError(
            error_number,
            f"atomic no-clobber publication unsupported for {destination}",
            str(destination),
        )

    raise OSError(error_number, os.strerror(error_number), str(destination))


def publish_path_no_clobber(source: Path, destination: Path) -> None:
    """Atomically publish one path without replacing an existing destination."""
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise OSError(
                getattr(errno, "ENOTSUP", errno.EINVAL),
                "atomic no-clobber publication unsupported: renameat2 unavailable",
                str(destination),
            )
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            _AT_FDCWD,
            os.fsencode(source),
            _AT_FDCWD,
            os.fsencode(destination),
            _RENAME_NOREPLACE,
        )
        if result == 0:
            return
        _raise_publish_error(ctypes.get_errno(), destination)

    if sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        renamex_np = getattr(libc, "renamex_np", None)
        if renamex_np is None:
            raise OSError(
                getattr(errno, "ENOTSUP", errno.EINVAL),
                "atomic no-clobber publication unsupported: renamex_np unavailable",
                str(destination),
            )
        renamex_np.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renamex_np.restype = ctypes.c_int
        result = renamex_np(
            os.fsencode(source),
            os.fsencode(destination),
            _RENAME_EXCL,
        )
        if result == 0:
            return
        _raise_publish_error(ctypes.get_errno(), destination)

    if sys.platform == "win32":
        os.rename(source, destination)
        return

    raise OSError(
        getattr(errno, "ENOTSUP", errno.EINVAL),
        f"atomic no-clobber publication unsupported on platform {sys.platform!r}",
        str(destination),
    )
