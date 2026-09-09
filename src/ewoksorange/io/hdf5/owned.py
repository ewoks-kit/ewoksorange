"""Reading a file this process writes."""

from .links import ReadOnlyLinksFile
from .live import LiveFile


class OwnedFile(LiveFile):
    """An HDF5 file the current process writes, read while it does.

    The file is only open while it is being read, and each read joins the mode
    the current process has it open with. Its external links are read read-only
    and unlocked, so raw data the current process does not write stays
    readable.
    """

    def __init__(self, name: str, **open_options):
        # Every linked file resolves its own mode: joined when the current
        # process already has it open, read-only and unlocked otherwise.
        super().__init__(name, external_open_options={}, **open_options)

    def open_h5_file(self, filename: str, **open_options) -> ReadOnlyLinksFile:
        return ReadOnlyLinksFile(filename, **open_options)
