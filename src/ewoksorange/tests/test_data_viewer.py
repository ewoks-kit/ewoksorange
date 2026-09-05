from contextlib import contextmanager

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


def test_forwards_tree_viewer_settings(ewoksorange_qtapp):
    """Verify DataViewer forwards settings to its tree viewer."""
    with _data_viewer(mode="r", locking=False) as viewer:
        assert viewer.treeViewer.mode == "r"
        assert viewer.treeViewer.locking is False
