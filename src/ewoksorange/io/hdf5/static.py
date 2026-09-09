"""Reading a file nobody writes."""

from .base import Hdf5File


class StaticFile(Hdf5File):
    """An HDF5 file nobody writes, kept open while it is read.

    Nothing has to be tolerated in this regime: the file is opened read-only,
    unlocked so no other process is blocked, and kept open because no read can
    see more than the previous one.
    """

    def __init__(
        self,
        name: str,
        keep_open: bool = True,
        mode: str = "r",
        locking: bool = False,
        **open_options,
    ) -> None:
        super().__init__(
            name, keep_open=keep_open, mode=mode, locking=locking, **open_options
        )
