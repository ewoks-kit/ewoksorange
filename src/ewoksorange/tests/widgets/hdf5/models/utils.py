"""Helpers shared by the model tests."""

import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator
from typing import List

import numpy
from silx.gui import qt
from silx.io import commonh5

from .....gui.widgets.hdf5.model.base import Hdf5TreeModel
from .....gui.widgets.hdf5.model.static import StaticFileTreeModel
from .....io.hdf5.utils import FileType

_EXTERNAL_OPEN = """
import sys
import h5py

for locking in (True, False, None):
    try:
        with h5py.File(sys.argv[1], mode=sys.argv[2], locking=locking):
            print("OPENED")
    except OSError:
        print("OSError:LOCKED")
"""


@dataclass(frozen=True)
class ExternalOpenResults:
    locking: str
    not_locking: str
    default: str


def open_from_other_process(filename: str, mode: str) -> ExternalOpenResults:
    """Attempt to open `filename` from a separate process."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _EXTERNAL_OPEN, filename, mode],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return ExternalOpenResults(*result.stdout.split())


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
def tree_model(
    model_class=StaticFileTreeModel, **open_options
) -> Iterator[Hdf5TreeModel]:
    """Create a model and guarantee its files are closed afterwards."""
    model = model_class(**open_options)
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


class MemoryTreeModel(Hdf5TreeModel):
    """Tree model serving content which is not on disk."""

    def __init__(self, contents: dict, parent=None, **open_options) -> None:
        super().__init__(parent, **open_options)
        self.contents = contents

    def exists(self, filename: str) -> bool:
        return filename in self.contents

    def openFile(self, filename: str) -> commonh5.File:
        h5file = commonh5.File(filename, mode="r")
        for name, value in self.contents[filename].items():
            h5file.add_node(commonh5.Dataset(name, numpy.asarray(value)))
        return h5file
