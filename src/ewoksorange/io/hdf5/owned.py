"""Reading a file this process writes."""

from typing import ContextManager

import h5py

from .access import open_for_reading
from .access import open_owned_for_reading
from .base import Hdf5File


class OwnedFile(Hdf5File):
    """An HDF5 file a task of this process may write, read while it does.

    Whether that task opens the file before, during or after a read here is a
    race nothing decides, so the file is read in the one mode which holds
    whichever order they come in: read-write, which a task asking for it joins
    and which joins a task already holding it. Nothing is written through it.
    See :func:`~ewoksorange.io.hdf5.access.open_owned_for_reading` for what a
    file which cannot be opened read-write falls back to.

    The files its external links point at are read read-only and unlocked, so
    raw data this process does not write stays readable.
    """

    def __init__(self, name: str, keep_open: bool = False, **open_options) -> None:
        # Every linked file resolves its own mode the same way: joined when
        # this process already has it open, read-only and unlocked otherwise.
        # Forcing read-only here would clash with the locking flags of a linked
        # file this process has open for writing.
        super().__init__(
            name, keep_open=keep_open, external_open_options={}, **open_options
        )

    def open_h5_file(self, filename: str, **open_options) -> ContextManager[h5py.File]:
        return open_owned_for_reading(filename, **open_options)

    def open_external_h5_file(
        self, filename: str, **open_options
    ) -> ContextManager[h5py.File]:
        return open_for_reading(filename, **open_options)
