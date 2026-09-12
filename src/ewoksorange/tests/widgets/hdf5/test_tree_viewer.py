from contextlib import contextmanager

import h5py
import pytest
from silx.gui import qt

from ....gui.widgets.hdf5.model.links import LinkAwareTreeModel
from ....gui.widgets.hdf5.model.static import StaticFileTreeModel
from ....gui.widgets.hdf5.tree_viewer import Hdf5TreeViewer
from .models.utils import open_from_other_process
from .models.utils import update_file
from .models.utils import wait_for_loading


@contextmanager
def _tree_viewer(model=None, toolbar=False, **open_options):
    """Create a `Hdf5TreeViewer` and guarantee its files are closed afterwards."""
    if model is None:
        model = StaticFileTreeModel(**open_options)
    viewer = Hdf5TreeViewer(model, toolbar=toolbar)
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


def test_toolbar_hidden_by_default(ewoksorange_qtapp):
    """Verify the toolbar is hidden unless requested."""
    with _tree_viewer() as viewer:
        assert viewer.toolBar().isHidden()
    with _tree_viewer(toolbar=True) as viewer:
        assert not viewer.toolBar().isHidden()


def test_refresh_preserves_mode_and_locking(ewoksorange_qtapp, h5file):
    """Verify refresh uses the configured mode and locking option."""
    with _tree_viewer(mode="a", locking=False) as viewer:
        update_file(viewer, h5file)
        (old_h5,) = viewer.h5Files

        root_index = viewer.treeView.model().index(0, 0)
        viewer.treeView.selectionModel().select(
            root_index, qt.QItemSelectionModel.ClearAndSelect
        )
        update_file(viewer, h5file)

        (h5,) = viewer.h5Files
        assert h5 is not old_h5
        assert h5.mode == "r+"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OPENED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OPENED"


def test_update_file_synchronizes_open_file(ewoksorange_qtapp, h5file):
    """Updating an open file replaces it without needing it to be selected."""
    synchronized = list()

    with _tree_viewer(mode="r") as viewer:
        update_file(viewer, h5file)
        (old_h5,) = viewer.h5Files

        viewer.sigH5FileSynchronized.connect(
            lambda removed, loaded: synchronized.append((removed, loaded))
        )
        update_file(viewer, h5file)

        (new_h5,) = viewer.h5Files
        assert new_h5 is not old_h5
        assert len(synchronized) == 1
        assert synchronized[0][0] is old_h5
        assert synchronized[0][1] is new_h5


def _toolbar_action(viewer, text):
    (action,) = [a for a in viewer.toolBar().actions() if a.text() == text]
    return action


def test_refresh_shortcuts(ewoksorange_qtapp):
    """Verify refresh is bound to both F5 and Ctrl+R."""
    with _tree_viewer(toolbar=True) as viewer:
        shortcuts = _toolbar_action(viewer, "Refresh").shortcuts()
        assert qt.QKeySequence(qt.Qt.Key_F5) in shortcuts
        assert qt.QKeySequence(qt.Qt.CTRL | qt.Qt.Key_R) in shortcuts


def test_expand_all_is_not_shallow(ewoksorange_qtapp, tmp_path):
    """Verify expanding selected items reaches beyond the first levels."""
    filename = str(tmp_path / "deep.h5")
    depth = 8
    with h5py.File(filename, "w") as f:
        f.create_group("/".join(f"g{i}" for i in range(depth)))

    with _tree_viewer(toolbar=True) as viewer:
        update_file(viewer, filename)
        treeView = viewer.treeView
        model = treeView.model()
        rootIndex = model.index(0, 0, qt.QModelIndex())
        treeView.selectionModel().select(
            rootIndex, qt.QItemSelectionModel.ClearAndSelect
        )

        _toolbar_action(viewer, "Expand all").trigger()

        expanded = 0
        index = rootIndex
        while model.hasChildren(index) and treeView.isExpanded(index):
            expanded += 1
            index = model.index(0, 0, index)
        assert expanded == depth


def test_context_menu_callback(ewoksorange_qtapp, h5file):
    """Verify custom actions can be added to the context menu of a node."""
    with _tree_viewer() as viewer:

        def addAction(event):
            for node in event.source().selectedH5Nodes(ignoreBrokenLinks=False):
                action = qt.QAction(f"Custom {node.name}", event.source())
                event.menu().addAction(action)

        viewer.addContextMenuCallback(addAction)
        update_file(viewer, h5file)

        treeView = viewer.treeView
        model = treeView.model()
        rootIndex = model.index(0, 0, qt.QModelIndex())
        treeView.setExpanded(rootIndex, True)
        datasetIndex = model.index(0, 0, rootIndex)
        treeView.selectionModel().select(
            datasetIndex, qt.QItemSelectionModel.ClearAndSelect
        )

        treeView._createContextMenu(treeView.visualRect(datasetIndex).center())

        labels = [
            action.text()
            for menu in treeView.findChildren(qt.QMenu)
            for action in menu.actions()
        ]
        assert "Custom /existing" in labels, labels


def test_update_file_does_not_block(ewoksorange_qtapp, h5file):
    """Verify background loading does not block the caller."""

    class _BackgroundTreeModel(StaticFileTreeModel):
        BACKGROUND_LOADING = True

    with _tree_viewer(model=_BackgroundTreeModel()) as viewer:
        viewer.updateFile(h5file)
        assert viewer.h5Files == ()
        assert viewer.treeModel.hasPendingOperations()

        wait_for_loading(viewer)

        (h5,) = viewer.h5Files
        assert h5["existing"][()] == 42


def test_update_file_blocks_by_default(ewoksorange_qtapp, h5file):
    """Verify a file is in the tree when updateFile returns by default."""
    with _tree_viewer() as viewer:
        viewer.updateFile(h5file)
        assert not viewer.treeModel.hasPendingOperations()
        (h5,) = viewer.h5Files
        assert h5["existing"][()] == 42


def test_refresh_external_access_model(ewoksorange_qtapp, h5file):
    """Verify refresh works for files which are not h5py objects."""
    with _tree_viewer(model=LinkAwareTreeModel(), toolbar=True) as viewer:
        update_file(viewer, h5file)
        (old_h5,) = viewer.h5Files

        rootIndex = viewer.treeView.model().index(0, 0, qt.QModelIndex())
        viewer.treeView.selectionModel().select(
            rootIndex, qt.QItemSelectionModel.ClearAndSelect
        )
        _toolbar_action(viewer, "Refresh").trigger()

        (h5,) = viewer.h5Files
        assert h5 is not old_h5
