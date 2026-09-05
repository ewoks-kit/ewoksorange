import logging
import os
from contextlib import contextmanager
from typing import Iterator
from typing import Optional
from typing import Sequence
from typing import Tuple

import h5py
import silx.io
from silx.gui import icons
from silx.gui import qt
from silx.gui.hdf5 import Hdf5ContextMenuEvent
from silx.gui.hdf5 import Hdf5TreeModel
from silx.gui.hdf5 import Hdf5TreeView
from silx.gui.hdf5 import NexusSortFilterProxyModel

_logger = logging.getLogger(__name__)


class Hdf5TreeViewer(qt.QWidget):
    """Browse the structure of files supported by silx.

    To create the widget

    .. code: python

        tree = Hdf5TreeViewer(parent)
        parent.layout().addWidget(tree)

    To close and refresh files

    .. code: python

        tree.updateFile("/path/to/file1.h5")
        tree.updateFile("/path/to/file2.h5")
        tree.closeFile("/path/to/file1.h5")

    To close all files

    .. code: python

        tree.closeAll()

    The toolbar is hidden by default. Enable it with
    `Hdf5TreeViewer(parent, toolbar=True)` or show it later through
    `toolBar()`. The keyboard shortcuts of the toolbar actions stay
    active while the toolbar is hidden.
    """

    sigH5FileLoaded = qt.Signal(object)
    """Emitted when a file was loaded into the tree."""

    sigH5FileRemoved = qt.Signal(object)
    """Emitted before a file is removed from the tree and closed."""

    sigH5FileSynchronized = qt.Signal(object, object)
    """Emitted with the old and the new file before the old file is closed."""

    sigSelectionActivated = qt.Signal()
    """Emitted when the user activates an item of the tree."""

    def __init__(
        self,
        parent=None,
        *,
        mode: str = "a",
        locking: Optional[bool] = None,
        toolbar: bool = False,
    ):
        super().__init__(parent)

        self._h5files = list()

        self.__treeView = Hdf5TreeView(self)
        self.__treeView.setExpandsOnDoubleClick(False)

        self.__toolBar = self.__createToolBar(self.__treeView)
        self.__treeModelSorted = self.__createTreeModel(self.__treeView)

        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.__toolBar)
        layout.addWidget(self.__treeView)

        self.__treeView.activated.connect(self.sigSelectionActivated)
        self.__treeView.addContextMenuCallback(self.__treeContextMenu)
        self.__customizeTreeModelColumns()

        self.__toolBar.setVisible(toolbar)

        self._mode = mode
        self._locking = locking

    @property
    def treeView(self) -> Hdf5TreeView:
        """The underlying silx tree view."""
        return self.__treeView

    @property
    def mode(self) -> str:
        """The mode used to open files."""
        return self._mode

    @property
    def locking(self) -> Optional[bool]:
        """The file-locking option used to open files."""
        return self._locking

    @property
    def h5Files(self) -> Tuple[h5py.File, ...]:
        """The currently opened HDF5 files."""
        return tuple(self._h5files)

    def toolBar(self) -> qt.QToolBar:
        """Return the toolbar of the tree, hidden by default.

        Use `toolBar().toggleViewAction()` to add a checkable entry to a menu.
        """
        return self.__toolBar

    def selectedH5Nodes(self, ignoreBrokenLinks: bool = True):
        """Return an iterator of `H5Node` objects for the selected items."""
        return self.__treeView.selectedH5Nodes(ignoreBrokenLinks=ignoreBrokenLinks)

    def addContextMenuCallback(self, callback):
        """Register a context menu callback on the tree view."""
        self.__treeView.addContextMenuCallback(callback)

    def __createTreeModel(self, treeView: Hdf5TreeView) -> NexusSortFilterProxyModel:
        treeModel = Hdf5TreeModel(treeView, ownFiles=False)
        treeModel.sigH5pyObjectLoaded.connect(self.__h5FileLoaded)
        treeModel.sigH5pyObjectRemoved.connect(self.__h5FileRemoved)
        treeModel.sigH5pyObjectSynchronized.connect(self.__h5FileSynchronized)
        treeModel.setDatasetDragEnabled(True)

        treeModelSorted = NexusSortFilterProxyModel(treeView)
        treeModelSorted.setSourceModel(treeModel)
        treeModelSorted.sort(0, qt.Qt.AscendingOrder)
        treeModelSorted.setSortCaseSensitivity(qt.Qt.CaseInsensitive)
        treeView.setModel(treeModelSorted)
        return treeModelSorted

    def __customizeTreeModelColumns(self):
        treeModel = self.__treeView.findHdf5TreeModel()
        columns = list(treeModel.COLUMN_IDS)
        columns.remove(treeModel.VALUE_COLUMN)
        columns.remove(treeModel.NODE_COLUMN)
        columns.remove(treeModel.DESCRIPTION_COLUMN)
        columns.insert(1, treeModel.DESCRIPTION_COLUMN)
        self.__treeView.header().setSections(columns)

    def __createToolBar(self, treeView: Hdf5TreeView) -> qt.QToolBar:
        toolbar = qt.QToolBar(self)
        toolbar.setIconSize(qt.QSize(16, 16))
        toolbar.setStyleSheet("QToolBar { border: 0px }")

        action = qt.QAction(toolbar)
        action.setIcon(icons.getQIcon("view-refresh"))
        action.setText("Refresh")
        action.setToolTip("Refresh all selected items")
        action.triggered.connect(self.__refreshSelected)
        action.setShortcut(qt.QKeySequence(qt.Qt.Key_F5))
        toolbar.addAction(action)
        treeView.addAction(action)
        self.__refreshAction = action

        # Another shortcut for refresh
        action = qt.QAction(toolbar)
        action.setShortcut(qt.QKeySequence(qt.Qt.CTRL | qt.Qt.Key_R))
        treeView.addAction(action)
        action.triggered.connect(self.__refreshSelected)

        action = qt.QAction(toolbar)
        # action.setIcon(icons.getQIcon("view-refresh"))
        action.setText("Close")
        action.setToolTip("Close selected item")
        action.triggered.connect(self.__removeSelected)
        action.setShortcut(qt.QKeySequence(qt.Qt.Key_Delete))
        treeView.addAction(action)
        self.__closeAction = action

        toolbar.addSeparator()

        action = qt.QAction(toolbar)
        action.setIcon(icons.getQIcon("tree-expand-all"))
        action.setText("Expand all")
        action.setToolTip("Expand all selected items")
        action.triggered.connect(self.__expandAllSelected)
        action.setShortcut(qt.QKeySequence(qt.Qt.CTRL | qt.Qt.Key_Plus))
        toolbar.addAction(action)
        treeView.addAction(action)
        self.__expandAllAction = action

        action = qt.QAction(toolbar)
        action.setIcon(icons.getQIcon("tree-collapse-all"))
        action.setText("Collapse all")
        action.setToolTip("Collapse all selected items")
        action.triggered.connect(self.__collapseAllSelected)
        action.setShortcut(qt.QKeySequence(qt.Qt.CTRL | qt.Qt.Key_Minus))
        toolbar.addAction(action)
        treeView.addAction(action)
        self.__collapseAllAction = action

        action = qt.QAction("&Sort file content", toolbar)
        action.setIcon(icons.getQIcon("tree-sort"))
        action.setToolTip("Toggle sorting of file content")
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(self.setContentSorted)
        toolbar.addAction(action)
        treeView.addAction(action)
        self._sortContentAction = action

        return toolbar

    def __iterModelIndices(
        self, max_depth: Optional[int] = None, indexes: Optional[Sequence] = None
    ) -> Iterator[Tuple[Tuple[qt.QModelIndex, int], qt.QModelIndex, int]]:
        selection = self.__treeView.selectionModel()
        if indexes is None:
            indexes = selection.selectedIndexes()
        while len(indexes) > 0:
            index = indexes.pop(0)
            if isinstance(index, tuple):
                index, depth = index
            else:
                depth = 0
            if index.column() != 0:
                continue
            if max_depth is not None and depth > max_depth:
                break
            yield indexes, index, depth

    @staticmethod
    def __getRootIndex(index: qt.QModelIndex):
        rootIndex = index
        while rootIndex.parent().isValid():
            rootIndex = rootIndex.parent()
        return rootIndex

    def __removeSelected(self):
        """Close selected items"""
        model = self.__treeView.model()
        h5files = set()
        selectedItems = []
        with self.__waitCursor():
            for _, index, _ in self.__iterModelIndices():
                rootIndex = self.__getRootIndex(index)
                relativePath = self.__getRelativePath(model, rootIndex, index)
                selectedItems.append((rootIndex.row(), relativePath))

                h5 = model.data(index, role=Hdf5TreeModel.H5PY_OBJECT_ROLE)
                h5files.add(h5.file)

            if not h5files:
                return

            model = self.__treeView.findHdf5TreeModel()
            for h5 in h5files:
                model.removeH5pyObject(h5)

    def __refreshSelected(self):
        """Refresh all selected items"""
        model = self.__treeView.model()
        selection = self.__treeView.selectionModel()
        selectedItems = []
        h5files = []
        with self.__waitCursor():
            for _, index, _ in self.__iterModelIndices():
                rootIndex = self.__getRootIndex(index)
                relativePath = self.__getRelativePath(model, rootIndex, index)
                selectedItems.append((rootIndex.row(), relativePath))

                h5 = model.data(rootIndex, role=Hdf5TreeModel.H5PY_OBJECT_ROLE)
                item = model.data(rootIndex, role=Hdf5TreeModel.H5PY_ITEM_ROLE)
                h5files.append((h5, item._openedPath))

            if not h5files:
                return

            for h5, filename in h5files:
                self.__synchronizeH5pyObject(h5, filename)

            itemSelection = qt.QItemSelection()
            for rootRow, relativePath in selectedItems:
                rootIndex = model.index(rootRow, 0, qt.QModelIndex())
                index = self.__indexFromPath(model, rootIndex, relativePath)
                if index is None:
                    continue
                indexEnd = model.index(
                    index.row(), model.columnCount() - 1, index.parent()
                )
                itemSelection.select(index, indexEnd)
            selection.select(itemSelection, qt.QItemSelectionModel.ClearAndSelect)

    def __synchronizeH5pyObject(self, h5, filename: Optional[str] = None):
        model = self.__treeView.findHdf5TreeModel()
        # This is buggy right now while h5py do not allow to close a file
        # while references are still used.
        # FIXME: The architecture have to be reworked to support this feature.
        # model.synchronizeH5pyObject(h5)

        if filename is None:
            filename = f"{h5.file.filename}::{h5.name}"
        row = model.h5pyObjectRow(h5)
        index = self.__treeView.model().index(row, 0, qt.QModelIndex())
        paths = self.__getPathFromExpandedNodes(self.__treeView, index)
        model.removeH5pyObject(h5)
        model.insertFile(filename, row)
        index = self.__treeView.model().index(row, 0, qt.QModelIndex())
        self.__expandNodesFromPaths(self.__treeView, index, paths)

    def __getRelativePath(self, model, rootIndex, index):
        """Returns a relative path from an index to his rootIndex.

        If the path is empty the index is also the rootIndex.
        """
        path = ""
        while index.isValid():
            if index == rootIndex:
                return path
            name = model.data(index)
            if path == "":
                path = name
            else:
                path = name + "/" + path
            index = index.parent()

        # index is not a children of rootIndex
        raise ValueError("index is not a children of the rootIndex")

    def __getPathFromExpandedNodes(self, view, rootIndex):
        """Return relative path from the root index of the extended nodes"""
        model = view.model()
        rootPath = None
        paths = []

        for indexes, index, depth in self.__iterModelIndices(indexes=[rootIndex]):
            if not view.isExpanded(index):
                continue

            node = model.data(index, role=Hdf5TreeModel.H5PY_ITEM_ROLE)
            path = node._getCanonicalName()
            if rootPath is None:
                rootPath = path
            path = path[len(rootPath) :]
            paths.append(path)

            for child in range(model.rowCount(index)):
                childIndex = model.index(child, 0, index)
                indexes.append((childIndex, depth + 1))
        return paths

    def __indexFromPath(self, model, rootIndex, path):
        elements = path.split("/")
        if elements[0] == "":
            elements.pop(0)
        index = rootIndex
        while len(elements) != 0:
            element = elements.pop(0)
            found = False
            for child in range(model.rowCount(index)):
                childIndex = model.index(child, 0, index)
                name = model.data(childIndex)
                if element == name:
                    index = childIndex
                    found = True
                    break
            if not found:
                return None
        return index

    def __expandNodesFromPaths(self, view, rootIndex, paths):
        model = view.model()
        for path in paths:
            index = self.__indexFromPath(model, rootIndex, path)
            if index is not None:
                view.setExpanded(index, True)

    @contextmanager
    def __waitCursor(self):
        qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
        try:
            yield
        finally:
            qt.QApplication.restoreOverrideCursor()

    def __expandAllSelected(self):
        """Expand all selected items of the tree."""
        with self.__waitCursor():
            self.__setExpanded(True)

    def __collapseAllSelected(self):
        """Collapse all selected items of the tree."""
        self.__setExpanded(False)

    def __setExpanded(self, expanded: bool):
        model = self.__treeView.model()
        for indexes, index, depth in self.__iterModelIndices(max_depth=2):
            if not model.hasChildren(index):
                continue
            self.__treeView.setExpanded(index, expanded)
            for row in range(model.rowCount(index)):
                childIndex = model.index(row, 0, index)
                indexes.append((childIndex, depth + 1))

    def __h5FileLoaded(self, loadedH5):
        self._h5files.append(loadedH5)
        self.sigH5FileLoaded.emit(loadedH5)

    def __h5FileRemoved(self, removedH5):
        # Emit before the close, so listeners drop their references first.
        self.sigH5FileRemoved.emit(removedH5)
        removedH5.close()
        self._h5files.remove(removedH5)

    def __h5FileSynchronized(self, removedH5, loadedH5):
        # Emit before the close, so listeners drop their references first.
        self.sigH5FileSynchronized.emit(removedH5, loadedH5)
        removedH5.close()
        self._h5files.remove(removedH5)

    def closeEvent(self, event):
        self.closeAll()

    def closeAll(self):
        """Close all currently opened files"""
        self.__treeView.findHdf5TreeModel().clear()

    def __getFileObject(self, filename):
        for h5file in self._h5files:
            if h5file.filename == filename:
                return h5file

    def closeFile(self, filename):
        h5file = self.__getFileObject(filename)
        model = self.__treeView.findHdf5TreeModel()
        model.removeH5pyObject(h5file)

    def updateFile(self, filename):
        if not os.path.exists(filename):
            return
        h5file = self.__getFileObject(filename)
        if h5file is not None:
            self.__refreshAction.trigger()
            return
        self.closeFile(filename)
        model = self.__treeView.findHdf5TreeModel()
        h5file = h5py.File(filename, mode=self._mode, locking=self._locking)
        try:
            model.sigH5pyObjectLoaded.emit(h5file, filename)
        except TypeError:
            # Support silx<2.0.0
            model.sigH5pyObjectLoaded.emit(h5file)
        try:
            model.insertH5pyObject(h5file, filename=filename)
        except TypeError:
            # Support silx<2.0.0
            model.insertH5pyObject(h5file)

    def setContentSorted(self, sort):
        """Set whether file content should be sorted or not.

        :param bool sort:
        """
        sort = bool(sort)
        if sort != self.isContentSorted():
            # save expanded nodes
            pathss = []
            root = qt.QModelIndex()
            model = self.__treeView.model()
            for i in range(model.rowCount(root)):
                index = model.index(i, 0, root)
                paths = self.__getPathFromExpandedNodes(self.__treeView, index)
                pathss.append(paths)

            self.__treeView.setModel(
                self.__treeModelSorted if sort else self.__treeModelSorted.sourceModel()
            )
            self._sortContentAction.setChecked(self.isContentSorted())

            # restore expanded nodes
            model = self.__treeView.model()
            for i in range(model.rowCount(root)):
                index = model.index(i, 0, root)
                paths = pathss.pop(0)
                self.__expandNodesFromPaths(self.__treeView, index, paths)

    def isContentSorted(self):
        """Returns whether the file content is sorted or not.

        :rtype: bool
        """
        return self.__treeView.model() is self.__treeModelSorted

    def __treeContextMenu(self, event: Hdf5ContextMenuEvent):
        """Called to populate the context menu"""
        selectedObjects = event.source().selectedH5Nodes(ignoreBrokenLinks=False)
        menu = event.menu()

        if not menu.isEmpty():
            menu.addSeparator()

        for obj in selectedObjects:
            h5 = obj.h5py_object

            if silx.io.is_file(h5):
                action = qt.QAction("Close %s" % obj.local_filename, event.source())
                action.triggered.connect(
                    lambda: self.__treeView.findHdf5TreeModel().removeH5pyObject(h5)
                )
                menu.addAction(action)
                action = qt.QAction(
                    "Synchronize %s" % obj.local_filename, event.source()
                )
                action.triggered.connect(lambda: self.__synchronizeH5pyObject(h5))
                menu.addAction(action)
