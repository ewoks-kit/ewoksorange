import pytest

from .....gui.widgets.hdf5.model.base import Hdf5TreeModel
from .....gui.widgets.hdf5.model.static import StaticFileTreeModel
from .utils import MemoryTreeModel
from .utils import opened_files
from .utils import tree_model


class _CountingTreeModel(StaticFileTreeModel):
    """Tree model recording the files it opens."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.opened = list()

    def openFile(self, filename: str):
        self.opened.append(filename)
        return super().openFile(filename)


def test_abstract(ewoksorange_qtapp):
    """Verify Hdf5TreeModel requires openFile to be implemented."""
    with pytest.raises(TypeError):
        Hdf5TreeModel()


def test_open_options_complete_the_defaults(ewoksorange_qtapp):
    """Verify given options are merged into DEFAULT_OPEN_OPTIONS."""
    with tree_model() as model:
        assert model.openOptions == {"mode": "r", "locking": False}
    with tree_model(mode="a") as model:
        assert model.openOptions == {"mode": "a", "locking": False}
    with tree_model(mode="a", locking=True, swmr=False) as model:
        assert model.openOptions == {"mode": "a", "locking": True, "swmr": False}


def test_open_file_is_the_only_entry_point(ewoksorange_qtapp, h5file):
    """Verify inserting and reinserting a file go through openFile."""
    with tree_model(_CountingTreeModel) as model:
        model.insertFile(h5file)
        assert model.opened == [h5file]
        (h5,) = opened_files(model)
        assert h5["existing"][()] == 42

        model.insertFile(h5file)
        assert model.opened == [h5file, h5file]
        assert len(opened_files(model)) == 2


def test_exists_defaults_to_the_file_system(ewoksorange_qtapp, h5file):
    """Verify exists reports on paths by default."""
    with tree_model() as model:
        assert model.exists(h5file)
        assert not model.exists(h5file + ".missing")


def test_content_which_is_not_on_disk(ewoksorange_qtapp):
    """Verify a model can serve content it makes up itself."""
    contents = {"memory.h5": {"data": [0, 1, 2]}}
    with tree_model(MemoryTreeModel, contents=contents) as model:
        assert model.exists("memory.h5")
        assert not model.exists("unknown.h5")

        model.insertFile("memory.h5")
        (h5file,) = opened_files(model)
        assert list(h5file["data"][()]) == [0, 1, 2]
