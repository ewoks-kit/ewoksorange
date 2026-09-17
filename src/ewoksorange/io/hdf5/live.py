"""Reading a file another process may be writing."""

from typing import ContextManager
from typing import Optional

import h5py
from silx.io import h5py_utils

from .access import retry_open
from .base import Hdf5File


class LiveFile(Hdf5File):
    """An HDF5 file another process may be writing, only open while it is read.

    Opening it read-only and unlocked is what leaves that writer free to start
    and unblocked once it has. Closing it between reads is what lets a later
    read see what the writer wrote since, because a handle kept open never sees
    writes which land after it was opened.

    A writer makes its writes visible by flushing the file, or by closing it,
    which flushes. Reads which land midway through a flush fail, so pass
    `retry_timeout` in seconds to retry them and `retry_period` in seconds to
    wait between those retries.
    """

    def __init__(
        self,
        name: str,
        retry_timeout: Optional[float] = None,
        retry_period: Optional[float] = None,
        mode: str = "r",
        locking: bool = False,
        **open_options,
    ) -> None:
        self._retry_timeout = retry_timeout
        self._retry_period = retry_period
        super().__init__(name, mode=mode, locking=locking, **open_options)

    def open_h5_file(self, filename: str, **open_options) -> ContextManager[h5py.File]:
        if self._retry_timeout is None:
            return h5py_utils.File(filename, **open_options)
        if self._retry_period is not None:
            # Not passed as `None`: that retries without waiting at all, where
            # leaving it out keeps the period silx defaults to.
            open_options["retry_period"] = self._retry_period
        return retry_open(filename, retry_timeout=self._retry_timeout, **open_options)
