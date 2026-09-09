import logging
import os
import time
from contextlib import contextmanager
from typing import Callable
from typing import Dict
from typing import Generator
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

import silx.io
from silx.gui import icons
from silx.gui import qt
from silx.gui.hdf5 import Hdf5ContextMenuEvent
from silx.gui.hdf5 import Hdf5TreeView
from silx.gui.hdf5 import NexusSortFilterProxyModel
from silx.gui.hdf5._utils import H5Node

from ....io.hdf5.utils import FileType
from .model.base import Hdf5TreeModel

_logger = logging.getLogger(__name__)

try:
    from silx._utils import nfs_cache_refresh as _nfs_cache_refresh
except ImportError:
    # Support silx<2.1.0
    def _nfs_cache_refresh(dirname: str) -> None:
        pass


_MAX_TREE_DEPTH = 10
"""Depth limit which stops expanding and collapsing recursive links."""


class Hdf5TreeViewer(qt.QWidget):
    """Browse the structure of files supported by silx.

    `model` decides which files can be browsed and how they are opened.

    The tree toolbar and its actions are extracted from the `silx view`
    application (``silx.app.view.Viewer``), which is a `QMainWindow` and cannot
    be embedded. Differences with that implementation are tagged with
    ``SILX DIFFERENCE`` comments.
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
        model: Hdf5TreeModel,
        parent: Optional[qt.QWidget] = None,
        *,
        toolbar: bool = False,
    ) -> None:
        super().__init__(parent)

        self._h5files: List[FileType] = list()
        self.__expandedPaths: Dict[str, List[str]] = dict()
        self.__synchronizing: bool = False
        self.__synchronizedH5: Optional[FileType] = None

        self.__treeView = Hdf5TreeView(self)
        self.__treeView.setExpandsOnDoubleClick(False)

        model.setParent(self.__treeView)
        self.__treeModel = model

        self.__toolBar = self.__createToolBar(self.__treeView)
        self.__treeModelSorted = self.__createSortedModel(self.__treeView)

        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.__toolBar)
        layout.addWidget(self.__treeView)

        self.__treeView.activated.connect(self.sigSelectionActivated)
        self.__treeView.addContextMenuCallback(self.__treeContextMenu)
        self.__customizeTreeModelColumns()

        self.__toolBar.setVisible(toolbar)

    @property
    def treeView(self) -> Hdf5TreeView:
        """The underlying silx tree view."""
        return self.__treeView

    @property
    def treeModel(self) -> Hdf5TreeModel:
        """The model which opens the files of the tree."""
        return self.__treeModel

    @property
    def h5Files(self) -> Tuple[FileType, ...]:
        """The currently opened HDF5 files."""
        return tuple(self._h5files)

    def toolBar(self) -> qt.QToolBar:
        """The toolbar of the tree, hidden by default."""
        return self.__toolBar

    def selectedH5Nodes(self, ignoreBrokenLinks: bool = True) -> Iterator[H5Node]:
        """Return an iterator of `H5Node` objects for the selected items."""
        return self.__treeView.selectedH5Nodes(ignoreBrokenLinks=ignoreBrokenLinks)

    def addContextMenuCallback(
        self, callback: Callable[[Hdf5ContextMenuEvent], None]
    ) -> None:
        """Register a context menu callback on the tree view."""
        self.__treeView.addContextMenuCallback(callback)

    def __createSortedModel(self, treeView: Hdf5TreeView) -> NexusSortFilterProxyModel:
        treeModel = self.__treeModel
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

    def __customizeTreeModelColumns(self) -> None:
        treeModel = self.__treeModel
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
        action.setShortcuts(
            [
                qt.QKeySequence(qt.Qt.Key_F5),
                qt.QKeySequence(qt.Qt.CTRL | qt.Qt.Key_R),
            ]
        )
        toolbar.addAction(action)
        treeView.addAction(action)
        self.__refreshAction = action

        action = qt.QAction(toolbar)
        # action.setIcon(icons.getQIcon("view-refresh"))
        action.setText("Close")
        action.setToolTip("Close selected item")
        action.triggered.connect(self.__removeSelected)
        action.setShortcut(qt.QKeySequence.Delete)
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
    def __getRootIndex(index: qt.QModelIndex) -> qt.QModelIndex:
        rootIndex = index
        while rootIndex.parent().isValid():
            rootIndex = rootIndex.parent()
        return rootIndex

    def __removeSelected(self) -> None:
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

            for h5 in h5files:
                self.__treeModel.removeH5pyObject(h5)

    def __refreshSelected(self) -> None:
        """Refresh all selected items"""
        model = self.__treeView.model()
        selection = self.__treeView.selectionModel()
        selectedItems = []
        h5roots = dict()
        with self.__waitCursor():
            for _, index, _ in self.__iterModelIndices():
                rootIndex = self.__getRootIndex(index)
                relativePath = self.__getRelativePath(model, rootIndex, index)
                selectedItems.append((rootIndex.row(), relativePath))

                h5 = model.data(rootIndex, role=Hdf5TreeModel.H5PY_OBJECT_ROLE)
                item = model.data(rootIndex, role=Hdf5TreeModel.H5PY_ITEM_ROLE)
                # SILX DIFFERENCE: a dict instead of a list. silx synchronizes
                # a root once per selected node under it, and every repeat acts
                # on a handle it already closed.
                h5roots[h5] = item._openedPath

            if not h5roots:
                return

            for h5, openedPath in h5roots.items():
                self.__synchronizeH5pyObject(h5, openedPath)

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

    def __synchronizeH5pyObject(
        self, h5: FileType, openedPath: Optional[str] = None
    ) -> None:
        """Reload the root `h5` in the background."""
        model = self.__treeModel
        if openedPath is None:
            openedPath = f"{h5.file.filename}::{h5.name}"
        row = model.h5pyObjectRow(h5)
        if row < 0:
            return
        sourceIndex = model.index(row, 0, qt.QModelIndex())

        index = self.__treeView.model().index(row, 0, qt.QModelIndex())
        self.__expandedPaths[openedPath] = self.__getPathFromExpandedNodes(
            self.__treeView, index
        )

        # SILX DIFFERENCE: not model.synchronizeH5pyObject, which reopens the
        # root by its file name instead of the path it was opened with.
        _nfs_cache_refresh(os.path.dirname(os.path.realpath(openedPath)))
        if model.BACKGROUND_LOADING:
            model.insertFileAsync(
                openedPath, row, synchronizingNode=model.nodeFromIndex(sourceIndex)
            )
            return

        # Loading in this thread keeps the file open as briefly as possible.
        self.__synchronizing = True
        self.__synchronizedH5 = None
        try:
            model.removeH5pyObject(h5)
            model.insertFile(openedPath, row)
        finally:
            self.__synchronizing = False

        self.__restoreExpandedNodes(openedPath)
        # Emit before the close, so listeners drop their references first.
        self.sigH5FileSynchronized.emit(h5, self.__synchronizedH5)
        h5.close()

    def __getRelativePath(
        self,
        model: qt.QAbstractItemModel,
        rootIndex: qt.QModelIndex,
        index: qt.QModelIndex,
    ) -> str:
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

    def __getPathFromExpandedNodes(
        self, view: Hdf5TreeView, rootIndex: qt.QModelIndex
    ) -> List[str]:
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

    def __indexFromPath(
        self,
        model: qt.QAbstractItemModel,
        rootIndex: qt.QModelIndex,
        path: str,
    ) -> Optional[qt.QModelIndex]:
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

    def __expandNodesFromPaths(
        self, view: Hdf5TreeView, rootIndex: qt.QModelIndex, paths: Sequence[str]
    ) -> None:
        model = view.model()
        for path in paths:
            index = self.__indexFromPath(model, rootIndex, path)
            if index is not None:
                view.setExpanded(index, True)

    @contextmanager
    def __waitCursor(self) -> Generator[None, None, None]:
        qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
        try:
            yield
        finally:
            qt.QApplication.restoreOverrideCursor()

    def __expandAllSelected(self) -> None:
        """Expand all selected items of the tree."""
        with self.__waitCursor():
            self.__setExpanded(True)

    def __collapseAllSelected(self) -> None:
        """Collapse all selected items of the tree."""
        self.__setExpanded(False)

    def __setExpanded(self, expanded: bool) -> None:
        model = self.__treeView.model()
        # The depth is fixed to avoid infinite loop with recursive links.
        for indexes, index, depth in self.__iterModelIndices(max_depth=_MAX_TREE_DEPTH):
            if not model.hasChildren(index):
                continue
            self.__treeView.setExpanded(index, expanded)
            for row in range(model.rowCount(index)):
                childIndex = model.index(row, 0, index)
                indexes.append((childIndex, depth + 1))

    def __h5FileLoaded(self, loadedH5: FileType, filename: str = "") -> None:
        self._h5files.append(loadedH5)
        if self.__synchronizing:
            self.__synchronizedH5 = loadedH5
            return
        self.__restoreExpandedNodes(filename or loadedH5.file.filename)
        self.sigH5FileLoaded.emit(loadedH5)

    def __h5FileRemoved(self, removedH5: FileType) -> None:
        if removedH5 not in self._h5files:
            # Removed before its background load finished.
            return
        self._h5files.remove(removedH5)
        if self.__synchronizing:
            # The caller emits sigH5FileSynchronized and closes the file.
            return
        # Emit before the close, so listeners drop their references first.
        self.sigH5FileRemoved.emit(removedH5)
        removedH5.close()

    def __h5FileSynchronized(self, removedH5: FileType, loadedH5: FileType) -> None:
        if removedH5 in self._h5files:
            self._h5files.remove(removedH5)
        self._h5files.append(loadedH5)
        self.__restoreExpandedNodes(loadedH5.file.filename)
        # Emit before the close, so listeners drop their references first.
        self.sigH5FileSynchronized.emit(removedH5, loadedH5)
        removedH5.close()

    def __restoreExpandedNodes(self, filename: str) -> None:
        paths = self.__expandedPaths.pop(filename, None)
        if not paths:
            return
        row = self.__treeModel.h5pyObjectRow(self.__getFileObject(filename))
        if row < 0:
            return
        index = self.__treeView.model().index(row, 0, qt.QModelIndex())
        self.__expandNodesFromPaths(self.__treeView, index, paths)

    def closeEvent(self, event: qt.QCloseEvent) -> None:
        self.closeAll()

    def closeAll(self) -> None:
        """Close all currently opened files"""
        # Clearing the model while a file is loading leaves the worker with an
        # item the model no longer knows about.
        self.waitForLoading()
        self.__expandedPaths.clear()
        self.__treeModel.clear()

    def waitForLoading(self, timeout: float = 60.0) -> None:
        """Wait until the files loading in the background are shown."""
        app = qt.QApplication.instance()
        if app is None:
            return
        deadline = time.monotonic() + timeout
        while self.__treeModel.hasPendingOperations():
            if time.monotonic() > deadline:
                _logger.warning("Loading did not finish within %s s", timeout)
                return
            app.processEvents()

    def __getFileObject(self, filename: str) -> Optional[FileType]:
        filename = os.path.normpath(os.path.abspath(filename))
        for h5file in self._h5files:
            if os.path.normpath(os.path.abspath(h5file.filename)) == filename:
                return h5file

    def closeFile(self, filename: str) -> None:
        """Close the file when it is open."""
        h5file = self.__getFileObject(filename)
        if h5file is None:
            return
        self.__treeModel.removeH5pyObject(h5file)

    def updateFile(self, filename: str) -> None:
        """Refresh the file when it is open, open it otherwise."""
        if not self.__treeModel.exists(filename):
            return
        h5file = self.__getFileObject(filename)
        if h5file is None:
            if self.__treeModel.BACKGROUND_LOADING:
                self.__treeModel.insertFileAsync(filename)
            else:
                with self.__waitCursor():
                    self.__treeModel.insertFile(filename)
        else:
            self.__synchronizeH5pyObject(h5file, filename)

    def setContentSorted(self, sort: bool) -> None:
        """Set whether file content should be sorted or not."""
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

    def isContentSorted(self) -> bool:
        """Returns whether the file content is sorted or not."""
        return self.__treeView.model() is self.__treeModelSorted

    def __removeH5pyObject(self, h5) -> None:
        self.__treeModel.removeH5pyObject(h5)

    def __treeContextMenu(self, event: Hdf5ContextMenuEvent) -> None:
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
                    lambda checked=False, h5=h5: self.__removeH5pyObject(h5)
                )
                menu.addAction(action)
                action = qt.QAction(
                    "Synchronize %s" % obj.local_filename, event.source()
                )
                action.triggered.connect(
                    lambda checked=False, h5=h5: self.__synchronizeH5pyObject(h5)
                )
                menu.addAction(action)
