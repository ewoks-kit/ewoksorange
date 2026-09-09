import h5py
import numpy
import pytest

from ....gui.widgets.hdf5.model import Hdf5TreeModel
from ....io.hdf5.live import LiveFile
from ....io.hdf5.owned import OwnedFile
from ....io.hdf5.static import StaticFile
from .utils import MemoryTreeModel
from .utils import opened_files
from .utils import tree_model


@pytest.fixture
def h5file(tmp_path):
    """Create a minimal HDF5 file holding a single dataset."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["existing"] = 42
    return filename


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


def test_file_class_defaults_to_static(ewoksorange_qtapp, h5file):
    """Verify files are kept open and read-only unless another class is given."""
    with tree_model() as model:
        assert model.fileClass is StaticFile

        model.insertFile(h5file)
        (h5root,) = opened_files(model)
        assert isinstance(h5root, StaticFile)
        assert h5root["existing"][()] == 42


@pytest.mark.parametrize("fileClass", [StaticFile, LiveFile, OwnedFile, h5py.File])
def test_the_file_class_is_a_constructor_argument(ewoksorange_qtapp, h5file, fileClass):
    """Verify every access class can be browsed, h5py included."""
    fileArguments = {"mode": "r"} if fileClass is h5py.File else {}
    with tree_model(fileClass, **fileArguments) as model:
        model.insertFile(h5file)
        (h5root,) = opened_files(model)
        assert isinstance(h5root, fileClass)
        assert h5root["existing"][()] == 42


def test_file_arguments_are_passed_to_the_file_class(ewoksorange_qtapp, h5file):
    """Verify the options given to the model are the ones files are opened with."""
    opened = {}

    class _TracingFile(LiveFile):
        def open_h5_file(self, filename, **open_options):
            opened[filename] = dict(open_options)
            return super().open_h5_file(filename, **open_options)

    with tree_model(_TracingFile, mode="r", locking=True) as model:
        assert model.fileArguments == {"mode": "r", "locking": True}

        model.insertFile(h5file)
        (h5root,) = opened_files(model)
        assert h5root["existing"][()] == 42
        assert opened[h5file] == {"mode": "r", "locking": True}


def test_open_file_is_the_only_entry_point(ewoksorange_qtapp, h5file):
    """Verify inserting and reinserting a file go through openFile."""
    opened = []

    class _CountingTreeModel(Hdf5TreeModel):
        def openFile(self, filename: str):
            opened.append(filename)
            return super().openFile(filename)

    model = _CountingTreeModel()
    try:
        model.insertFile(h5file)
        assert opened == [h5file]
        (h5root,) = opened_files(model)
        assert h5root["existing"][()] == 42

        model.insertFile(h5file)
        assert opened == [h5file, h5file]
        assert len(opened_files(model)) == 2
    finally:
        for h5root in opened_files(model):
            h5root.close()
        model.clear()


def test_files_are_not_held_open_by_a_reopening_class(ewoksorange_qtapp, h5file):
    """Verify another writer can modify a file in the model."""
    with tree_model(LiveFile) as model:
        model.insertFile(h5file)
        (h5root,) = opened_files(model)
        assert h5root["existing"][()] == 42

        # Exclusive write access while the file is in the model.
        with h5py.File(h5file, "a", locking=True) as f:
            f["existing"][()] = 7

        assert h5root["existing"][()] == 7


def test_external_links_are_followed(ewoksorange_qtapp, linked_h5file):
    """Verify a linked file is browsable through the model."""
    master, _ = linked_h5file
    with tree_model(OwnedFile) as model:
        model.insertFile(master)
        (h5root,) = opened_files(model)
        assert numpy.array_equal(h5root["linked/data"][()], [0, 1, 2, 3])


def test_exists_defaults_to_the_file_system(ewoksorange_qtapp, h5file):
    """Verify exists reports on paths by default."""
    with tree_model() as model:
        assert model.exists(h5file)
        assert not model.exists(h5file + ".missing")


def test_content_which_is_not_on_disk(ewoksorange_qtapp):
    """Verify a model can serve content it makes up itself."""
    contents = {"memory.h5": {"data": [0, 1, 2]}}
    model = MemoryTreeModel(contents)
    try:
        assert model.exists("memory.h5")
        assert not model.exists("unknown.h5")

        model.insertFile("memory.h5")
        (h5file,) = opened_files(model)
        assert list(h5file["data"][()]) == [0, 1, 2]
    finally:
        for h5file in opened_files(model):
            h5file.close()
        model.clear()


def test_background_loading_is_off_by_default(ewoksorange_qtapp):
    """Verify reading in a worker thread is asked for explicitly."""
    with tree_model() as model:
        assert not model.backgroundLoading
    with tree_model(backgroundLoading=True) as model:
        assert model.backgroundLoading
