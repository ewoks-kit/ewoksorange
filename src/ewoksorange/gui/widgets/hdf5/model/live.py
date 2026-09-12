"""Browsing a file another process may be writing."""

from types import MappingProxyType
from typing import Any
from typing import Mapping

from .....io.hdf5.live import LiveFile
from .base import Hdf5TreeModel


class LiveFileTreeModel(Hdf5TreeModel):
    """Browse a file another process may be writing.

    Reading read-only and unlocked is what leaves that writer unblocked. The
    file is closed between reads on top of that, because a handle kept open
    never sees anything written after it was opened.
    """

    # Unlocked is what does not block the writer, so it is not left to a
    # default of the library underneath.
    DEFAULT_OPEN_OPTIONS: Mapping[str, Any] = MappingProxyType(
        {"mode": "r", "locking": False}
    )

    FILE_CLASS = LiveFile
    """The :class:`~ewoksorange.io.hdf5.LiveFile` derived class to browse."""

    def openFile(self, filename: str) -> LiveFile:
        return self.FILE_CLASS(filename, **self._open_options)
