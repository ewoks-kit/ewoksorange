"""Opening HDF5 files for reading, whichever process is writing them.

The cases covered are:

* a file no process has open for writing, which must not be locked when it is
  read read-only
* a file another process currently has open for writing, like a running data
  acquisition, which must be read read-only and without locking
* a file the current process currently has open for writing, or will open for
  writing later, whose external links must still be read read-only and without
  locking (see :class:`~ewoksorange.io.hdf5.links.ReadOnlyLinksFile`)

The last two are mutually exclusive: HDF5 allows a single writer, so while the
current process has a file open for writing, no other process can have it open
for writing.
"""

import os
from contextlib import contextmanager
from typing import Generator
from typing import Optional

import h5py
from silx.io import h5py_utils


def process_open_mode(filename: str) -> Optional[str]:
    """Return the mode the current process currently has `filename` open with.

    `None` when the current process does not have it open. Says nothing about
    other processes: their handles are not visible here.
    """
    path = os.path.realpath(filename)
    for h5id in h5py.h5f.get_obj_ids(types=h5py.h5f.OBJ_FILE):
        try:
            name = h5id.name
            if isinstance(name, bytes):
                name = name.decode()
            if os.path.realpath(name) != path:
                continue
            intent = h5id.get_intent()
        except (ValueError, RuntimeError, OSError):
            # Another thread can close a file while its identifiers are listed.
            continue
        return "r+" if intent == h5py.h5f.ACC_RDWR else "r"
    return None


def open_for_reading(filename: str, **open_options) -> h5py.File:
    """Open `filename` for reading, joining the handle the current process
    already has when it has one. Never creates the file.

    Each mode is tried once: opening a file which another process is writing
    fails often enough that retrying here would multiply the time this process
    holds handles on it.
    """
    if "mode" in open_options or "locking" in open_options:
        raise TypeError("the access mode and file locking are determined here")

    # "best-effort" joins a handle taken with the default locking, `True` does not
    for locking in (False, "best-effort"):
        try:
            return h5py_utils.File(filename, mode="r", locking=locking, **open_options)
        except OSError:
            pass

    return h5py_utils.File(
        filename, mode=process_open_mode(filename) or "r+", **open_options
    )


@contextmanager
def read_access(
    filename: str, retry_timeout: Optional[float] = None, **open_options
) -> Generator[h5py.File, None, None]:
    """Open an HDF5 file for reading.

    See :func:`open_for_reading` for the mode the file ends up being opened
    with. Reading is unlocked whenever it can be, so a process which currently
    has the file open for writing is not blocked.

    `retry_timeout` in seconds retries the reads which fail because another
    process is busy writing the file.

    Use :class:`~ewoksorange.io.hdf5.links.ReadOnlyLinksFile` for a
    file the current process will open for writing later.
    """
    if open_options.pop("mode", "r") not in (None, "r"):
        raise ValueError("must be opened read-only")

    if retry_timeout is None:
        h5file = open_for_reading(filename, **open_options)
        try:
            yield h5file
        finally:
            h5file.close()
        return

    with _retry_read_access(
        filename, retry_timeout=retry_timeout, **open_options
    ) as h5file:
        yield h5file


@h5py_utils.retry_contextmanager()
def _retry_read_access(
    filename: str, **open_options
) -> Generator[h5py.File, None, None]:
    h5file = open_for_reading(filename, **open_options)
    try:
        yield h5file
    finally:
        h5file.close()


def external_link_filename(link: h5py.ExternalLink, h5file: h5py.File) -> str:
    """Return the absolute file name an external link points to."""
    filename = link.filename
    if os.path.isabs(filename):
        return filename
    return os.path.abspath(os.path.join(os.path.dirname(h5file.filename), filename))
