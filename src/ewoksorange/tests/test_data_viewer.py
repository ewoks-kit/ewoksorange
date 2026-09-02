from contextlib import contextmanager

import h5py
import pytest
from silx.gui import qt

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
def h5file(tmp_path):
    """Create a minimal HDF5 file holding a single dataset."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["existing"] = 42
    return filename


def test_default_tree_viewer_settings(ewoksorange_qtapp):
    """Verify DataViewer passes the default mode and locking to its tree viewer.

    The mode and locking behavior itself is tested on `Hdf5TreeViewer` in
    `test_hdf5_tree_viewer.py`.
    """
    with _data_viewer() as viewer:
        assert viewer.treeViewer._mode == "a"
        assert viewer.treeViewer._locking is None


def test_delegates_to_tree_viewer(ewoksorange_qtapp, h5file):
    """Verify DataViewer forwards settings and file operations to its tree viewer."""
    with _data_viewer(mode="r", locking=False) as viewer:
        assert viewer.treeViewer._mode == "r"
        assert viewer.treeViewer._locking is False

        viewer.updateFile(h5file)
        (h5,) = viewer.treeViewer._h5files
        assert h5.mode == "r"
        assert h5["existing"][()] == 42

        viewer.closeFile(h5file)
        assert viewer.treeViewer._h5files == []

        viewer.updateFile(h5file)
        viewer.closeAll()
        assert viewer.treeViewer._h5files == []
