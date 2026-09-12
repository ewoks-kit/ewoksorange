import h5py
import numpy
import pytest

from .....gui.widgets.hdf5.model.links import LinkAwareTreeModel
from .....gui.widgets.hdf5.model.owned import OwnedFileLinksTreeModel
from .....io.hdf5.links import LinkAwareFile
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
    """Verify the external access models open files read-only."""
    with tree_model(LinkAwareTreeModel) as model:
        assert model.openOptions == {"mode": "r", "locking": False}
    with tree_model(OwnedFileLinksTreeModel) as model:
        assert model.openOptions == {}


def test_external_link_in_the_tree(ewoksorange_qtapp, linked_h5file):
    """Verify a linked file is browsable through the model."""
    master, target = linked_h5file
    with tree_model(LinkAwareTreeModel) as model:
        model.insertFile(master)
        (h5root,) = opened_files(model)
        assert isinstance(h5root, LinkAwareFile)
        assert numpy.array_equal(h5root["linked/data"][()], [0, 1, 2, 3])
        assert h5root["linked"].file.filename == target


def test_read_access_while_open_for_writing(ewoksorange_qtapp, linked_h5file):
    """Verify a file open for writing in this process is browsable."""
    master, _ = linked_h5file
    with h5py.File(master, "a"):
        with tree_model(OwnedFileLinksTreeModel) as model:
            model.insertFile(master)
            (h5root,) = opened_files(model)
            assert h5root.mode == "r+"
            assert h5root["linked"].file.mode == "r"
