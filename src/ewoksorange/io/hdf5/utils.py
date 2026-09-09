"""Types and predicates shared by everything reading HDF5."""

from typing import List
from typing import Union

import h5py
import silx.io.utils
from silx.io import commonh5

from .links import LinkAwareFile
from .links import LinkAwareGroup

FileType = Union[h5py.File, commonh5.File, LinkAwareFile]
"""An HDF5 file, or one of the objects standing in for one."""

GroupType = Union[h5py.Group, commonh5.Group, LinkAwareGroup]
"""An HDF5 group. A file is a group."""

DatasetType = Union[h5py.Dataset, commonh5.Dataset]
"""An HDF5 dataset."""


def is_file(item) -> bool:
    """Return whether `item` is an HDF5 file."""
    return silx.io.utils.is_file(item)


def is_group(item) -> bool:
    """Return whether `item` is an HDF5 group. A file is a group."""
    return silx.io.utils.is_group(item)


def is_dataset(item) -> bool:
    """Return whether `item` is an HDF5 dataset."""
    return silx.io.utils.is_dataset(item)


def is_softlink(item) -> bool:
    """Return whether `item` is an HDF5 soft link."""
    return silx.io.utils.is_softlink(item)


def is_externallink(item) -> bool:
    """Return whether `item` is an HDF5 external link."""
    return silx.io.utils.is_externallink(item)


def split_h5data_path(data_path: str) -> List[str]:
    """Split an HDF5 path into its names."""
    return [name for name in data_path.split("/") if name]
