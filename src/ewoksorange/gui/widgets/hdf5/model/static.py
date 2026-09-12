from types import MappingProxyType
from typing import Any
from typing import Mapping

import h5py

from .base import Hdf5TreeModel


class StaticFileTreeModel(Hdf5TreeModel):
    """Tree model which keeps the files it browses open."""

    DEFAULT_OPEN_OPTIONS: Mapping[str, Any] = MappingProxyType(
        {"mode": "r", "locking": False}
    )

    def openFile(self, filename: str) -> h5py.File:
        return h5py.File(filename, **self._open_options)
