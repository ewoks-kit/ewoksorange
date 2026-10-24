"""Helpers shared by the HDF5 widget tests."""

from contextlib import contextmanager
from typing import Dict
from typing import Iterator
from typing import List

import numpy
from silx.gui import qt
from silx.io import commonh5

from ....gui.widgets.hdf5.model import Hdf5TreeModel
from ....io.hdf5.utils import FileType


def wait_for_loading(viewer, timeout: float = 60.0) -> None:
    """Wait until the viewer finished loading files."""
    viewer.waitForLoading(timeout)
    assert not viewer.treeModel.hasPendingOperations(), "loading did not finish"
    qt.QApplication.instance().processEvents()


def update_file(viewer, filename: str) -> None:
    """Update a file in a viewer and wait until it is loaded."""
    viewer.updateFile(filename)
    wait_for_loading(viewer)


@contextmanager
def tree_model(*args, **fileArguments) -> Iterator[Hdf5TreeModel]:
    """Create a model and guarantee its files are closed afterwards."""
    model = Hdf5TreeModel(*args, **fileArguments)
    try:
        yield model
    finally:
        for h5file in opened_files(model):
            h5file.close()
        model.clear()


def opened_files(model: Hdf5TreeModel) -> List[FileType]:
    """Return the files currently in the model."""
    return [
        model.data(
            model.index(row, 0, qt.QModelIndex()), Hdf5TreeModel.H5PY_OBJECT_ROLE
        )
        for row in range(model.rowCount(qt.QModelIndex()))
    ]


class MemoryFile(commonh5.File):
    """HDF5 file whose content is not on disk."""

    def __init__(self, name: str, contents: Dict[str, dict]) -> None:
        super().__init__(name, mode="r")
        for dataset_name, value in contents[name].items():
            self.add_node(commonh5.Dataset(dataset_name, numpy.asarray(value)))


class MemoryTreeModel(Hdf5TreeModel):
    """Tree model serving content which is not on disk."""

    def __init__(self, contents: Dict[str, dict], parent=None, **fileArguments) -> None:
        super().__init__(MemoryFile, parent, contents=contents, **fileArguments)
        self.contents = contents

    def exists(self, filename: str) -> bool:
        return filename in self.contents
