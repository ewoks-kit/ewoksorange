from contextlib import contextmanager

import h5py
import pytest
from silx.gui import qt
from silx.gui.data.DataViewerFrame import DataViewerFrame

from ..gui.widgets.data_viewer import DataViewer


@contextmanager
def _data_viewer(**kwargs):
    """Create a `DataViewer` and guarantee its files are closed afterwards."""
    viewer = DataViewer(None, **kwargs)
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
    """Verify DataViewer forwards settings to its tree viewer."""
    with _data_viewer(mode="r", locking=False) as viewer:
        assert viewer.treeViewer.mode == "r"
        assert viewer.treeViewer.locking is False


def test_loaded_and_removed_file_updates_data_panel(ewoksorange_qtapp, h5files):
    """The data panel displays a loaded file and clears it when it is closed."""
    with _data_viewer(mode="r") as viewer:
        data_panel = _data_panel(viewer)

        viewer.updateFile(h5files[0])
        (h5file,) = viewer.treeViewer.h5Files
        assert data_panel.data() is h5file

        viewer.closeFile(h5files[0])
        assert data_panel.data() is None


def test_synchronized_file_updates_data_panel(ewoksorange_qtapp, h5files):
    """Synchronizing a file replaces the displayed object with its new version."""
    with _data_viewer(mode="r") as viewer:
        viewer.updateFile(h5files[0])
        (old_h5file,) = viewer.treeViewer.h5Files
        viewer.displayData(old_h5file["existing"])

        with h5py.File(h5files[1], "r") as new_h5file:
            viewer.treeViewer.sigH5FileSynchronized.emit(old_h5file, new_h5file)

            synchronized_data = _data_panel(viewer).data()
            assert synchronized_data.file.filename == new_h5file.filename
            assert synchronized_data.name == "/existing"
            assert synchronized_data[()] == 1

            viewer.displayData(None)
