"""Browsing a file whose external links have their own regime."""

from types import MappingProxyType
from typing import Any
from typing import Mapping

from .....io.hdf5.links import LinkAwareFile
from .base import Hdf5TreeModel


class LinkAwareTreeModel(Hdf5TreeModel):
    """Browse a file whose external links need their own open options.

    The links point at other files, which are in a regime of their own.
    """

    DEFAULT_OPEN_OPTIONS: Mapping[str, Any] = MappingProxyType(
        {"mode": "r", "locking": False}
    )

    FILE_CLASS = LinkAwareFile
    """The :class:`~ewoksorange.io.hdf5.links.LinkAwareFile` to browse."""

    def openFile(self, filename: str) -> LinkAwareFile:
        return self.FILE_CLASS(filename, **self._open_options)
