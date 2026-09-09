"""Browsing a file this process writes."""

from types import MappingProxyType
from typing import Any
from typing import Mapping

from .....io.hdf5.links import ReadOnlyLinksFile
from .....io.hdf5.owned import OwnedFile
from .links import LinkAwareTreeModel
from .live import LiveFileTreeModel


class OwnedFileTreeModel(LiveFileTreeModel):
    """Browse a file this process writes.

    The file is reopened on every read, joining the mode the current process
    has it open with. Its external links are read read-only and unlocked.
    """

    DEFAULT_OPEN_OPTIONS: Mapping[str, Any] = MappingProxyType({})

    FILE_CLASS = OwnedFile


class OwnedFileLinksTreeModel(LinkAwareTreeModel):
    """Browse a file this process writes, keeping it open.

    Its external links are read read-only and unlocked. Pass `mode="a"` when
    the current process will open the file for writing later.
    """

    DEFAULT_OPEN_OPTIONS: Mapping[str, Any] = MappingProxyType({})

    FILE_CLASS = ReadOnlyLinksFile
