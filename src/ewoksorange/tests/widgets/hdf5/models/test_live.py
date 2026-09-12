import h5py
import numpy
import pytest

from .....gui.widgets.hdf5.model.live import LiveFileTreeModel
from .....gui.widgets.hdf5.model.owned import OwnedFileTreeModel
from .....io.hdf5.live import LiveFile
from .....io.hdf5.owned import OwnedFile
from .utils import opened_files
from .utils import tree_model


@pytest.fixture
def linked_h5file(tmp_path):
    """Create a file with an external link to a second file."""
    target = str(tmp_path / "target.h5")
    with h5py.File(target, "w") as f:
        f["entry/data"] = numpy.arange(4)

    master = str(tmp_path / "master.h5")
    with h5py.File(master, "w") as f:
        f["linked"] = h5py.ExternalLink("target.h5", "/entry")
    return master, target


def test_default_open_options(ewoksorange_qtapp):
    """Verify the reopening models open files read-only."""
    with tree_model(LiveFileTreeModel) as model:
        assert model.openOptions == {"mode": "r", "locking": False}
    with tree_model(OwnedFileTreeModel) as model:
        assert model.openOptions == {}


def test_files_are_not_held_open(ewoksorange_qtapp, h5file):
    """Verify another writer can modify a file in the model."""
    with tree_model(LiveFileTreeModel) as model:
        model.insertFile(h5file)
        (h5root,) = opened_files(model)
        assert isinstance(h5root, LiveFile)
        assert h5root["existing"][()] == 42

        # Exclusive write access while the file is in the model.
        with h5py.File(h5file, "a", locking=True) as f:
            f["existing"][()] = 7

        assert h5root["existing"][()] == 7


def test_read_access_model(ewoksorange_qtapp, linked_h5file):
    """Verify OwnedFileTreeModel follows external links."""
    master, _ = linked_h5file
    with tree_model(OwnedFileTreeModel) as model:
        model.insertFile(master)
        (h5root,) = opened_files(model)
        assert isinstance(h5root, OwnedFile)
        assert numpy.array_equal(h5root["linked/data"][()], [0, 1, 2, 3])


def test_file_class_can_be_replaced(ewoksorange_qtapp, h5file):
    """Verify the proxy used by the model can be replaced."""
    opened = []

    class _TracingFile(LiveFile):
        def open_h5_file(self, filename, **open_options):
            opened.append(filename)
            return super().open_h5_file(filename, **open_options)

    class _TracingTreeModel(LiveFileTreeModel):
        FILE_CLASS = _TracingFile

    with tree_model(_TracingTreeModel) as model:
        model.insertFile(h5file)
        (h5root,) = opened_files(model)
        assert isinstance(h5root, _TracingFile)

        count = len(opened)
        assert h5root["existing"][()] == 42
        assert len(opened) > count
        assert set(opened) == {h5file}
