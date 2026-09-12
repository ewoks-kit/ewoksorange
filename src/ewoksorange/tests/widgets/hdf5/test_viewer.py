from contextlib import contextmanager

import h5py
import pytest
from silx.gui import qt
from silx.gui.data.DataViewerFrame import DataViewerFrame

from ....gui.widgets.hdf5.model.static import StaticFileTreeModel
from ....gui.widgets.hdf5.viewer import Hdf5Viewer
from .models.utils import MemoryTreeModel
from .models.utils import update_file


@contextmanager
def _hdf5_viewer(model=None, displayOnLoad=False, **open_options):
    """Create a `Hdf5Viewer` and guarantee its files are closed afterwards."""
    if model is None:
        model = StaticFileTreeModel(**open_options)
    viewer = Hdf5Viewer(model, displayOnLoad=displayOnLoad)
    try:
        yield viewer
    finally:
        viewer.closeAll()
        viewer.deleteLater()
        qt.QCoreApplication.sendPostedEvents(None, qt.QEvent.Type.DeferredDelete)


@pytest.fixture
def h5files(tmp_path):
    """Create two HDF5 files containing the same dataset."""
    filenames = []
    for index in range(2):
        filename = str(tmp_path / f"data{index}.h5")
        with h5py.File(filename, "w") as h5file:
            h5file["existing"] = index
        filenames.append(filename)
    return filenames


def _data_panel(viewer):
    return viewer.findChild(DataViewerFrame)


def test_forwards_tree_viewer_settings(ewoksorange_qtapp):
    """Verify Hdf5Viewer forwards settings to its tree viewer."""
    with _hdf5_viewer(mode="a", locking=True) as viewer:
        options = viewer.treeViewer.treeModel.openOptions
        assert options == {"mode": "a", "locking": True}


def test_loaded_and_removed_file_updates_data_panel(ewoksorange_qtapp, h5files):
    """The data panel displays a loaded file and clears it when it is closed."""
    with _hdf5_viewer(mode="r", displayOnLoad=True) as viewer:
        data_panel = _data_panel(viewer)

        update_file(viewer.treeViewer, h5files[0])
        (h5file,) = viewer.treeViewer.h5Files
        assert data_panel.data() is h5file

        viewer.closeFile(h5files[0])
        assert data_panel.data() is None


def test_synchronized_file_updates_data_panel(ewoksorange_qtapp, h5files):
    """Synchronizing a file replaces the displayed object with its new version."""
    with _hdf5_viewer(mode="r") as viewer:
        update_file(viewer.treeViewer, h5files[0])
        (old_h5file,) = viewer.treeViewer.h5Files
        viewer.displayData(old_h5file["existing"])

        with h5py.File(h5files[1], "r") as new_h5file:
            viewer.treeViewer.sigH5FileSynchronized.emit(old_h5file, new_h5file)

            synchronized_data = _data_panel(viewer).data()
            assert synchronized_data.file.filename == new_h5file.filename
            assert synchronized_data.name == "/existing"
            assert synchronized_data[()] == 1

            viewer.displayData(None)


def test_forwards_tree_model(ewoksorange_qtapp):
    """Verify Hdf5Viewer forwards a custom model to its tree viewer."""
    model = StaticFileTreeModel(mode="r")
    with _hdf5_viewer(model=model) as viewer:
        assert viewer.treeViewer.treeModel is model


def test_updated_file_keeps_displayed_dataset(ewoksorange_qtapp, h5files):
    """Refreshing a file keeps the data panel on the displayed dataset."""
    with _hdf5_viewer(mode="r") as viewer:
        update_file(viewer.treeViewer, h5files[0])
        (h5file,) = viewer.treeViewer.h5Files
        viewer.displayData(h5file["existing"])

        update_file(viewer.treeViewer, h5files[0])

        data = _data_panel(viewer).data()
        assert data.name == "/existing"
        assert data[()] == 0

        viewer.displayData(None)


def test_in_memory_model_feeds_data_panel(ewoksorange_qtapp):
    """Verify the data panel displays content which is not on disk."""
    contents = {"memory.h5": {"data": [0, 1, 2]}}
    with _hdf5_viewer(model=MemoryTreeModel(contents), displayOnLoad=True) as viewer:
        update_file(viewer.treeViewer, "memory.h5")
        (h5file,) = viewer.treeViewer.h5Files
        assert _data_panel(viewer).data() is h5file

        viewer.displayData(h5file["data"])
        assert list(_data_panel(viewer).data()[()]) == [0, 1, 2]

        viewer.displayData(None)


def test_no_display_on_load_by_default(ewoksorange_qtapp, h5files):
    """Verify a loaded file is not shown until it is asked for."""
    with _hdf5_viewer(mode="r") as viewer:
        update_file(viewer.treeViewer, h5files[0])
        (h5file,) = viewer.treeViewer.h5Files
        assert _data_panel(viewer).data() is None

        viewer.displayData(h5file["existing"])
        assert _data_panel(viewer).data()[()] == 0
        viewer.displayData(None)
