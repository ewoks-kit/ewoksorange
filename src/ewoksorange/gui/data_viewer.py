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
from silx.gui.data.DataViewerFrame import DataViewerFrame
from silx.gui.hdf5 import Hdf5ContextMenuEvent
from silx.gui.hdf5 import Hdf5TreeModel
from silx.gui.hdf5 import Hdf5TreeView
from silx.gui.hdf5 import NexusSortFilterProxyModel

_logger = logging.getLogger(__name__)


class DataViewer(qt.QWidget):
    """Browse data from files supported by silx.

    To create the widget

    .. code: python

        viewer = DataViewer(parent)
        viewer.setVisible(True)
        parent.layout().addWidget(viewer)

    To close and refresh files

    .. code: python

        viewer.updateFile("/path/to/file1.h5")
        viewer.updateFile("/path/to/file2.h5")
        viewer.closeFile("/path/to/file1.h5")

    To close all files

    .. code: python

        viewer.closeAll()
    """

    def __init__(self, parent):
        super().__init__(parent)

        self._h5files = list()

        # Do we need buttons for these?
        # silx.config.DEFAULT_PLOT_IMAGE_Y_AXIS_ORIENTATION = "downward"
        # silx.config.DEFAULT_PLOT_IMAGE_Y_AXIS_ORIENTATION = "upward"
        # silx.config.DEFAULT_PLOT_BACKEND = "matplotlib"
        # silx.config.DEFAULT_PLOT_BACKEND = "opengl"

        self.__treePanel = qt.QSplitter(self)
        self.__treePanel.setOrientation(qt.Qt.Vertical)

        self.__dataPanel = DataViewerFrame(self)

        self.__treeview = Hdf5TreeView(self)
        self.__treeview.setExpandsOnDoubleClick(False)

        self.__treeWindow = self.__createTreeWindow(self.__treeview)
        self.__treeModelSorted = self.__createTreeModel(self.__treeview)

        self.__treePanel.addWidget(self.__treeWindow)
        self.__treePanel.setStretchFactor(1, 1)
        self.__treePanel.setCollapsible(0, False)

        self.__mainWidget = self.__createMainWidget(self.__treePanel, self.__dataPanel)

        self.__setLayout(self.__mainWidget)

        self.__treeview.activated.connect(self.displaySelectedData)
        self.__treeview.addContextMenuCallback(self.treeContextMenu)
        self.__customizeTreeModelColumns()

    def __setLayout(self, mainWidget):
        layout = qt.QVBoxLayout()
        layout.addWidget(mainWidget)
        layout.setStretchFactor(mainWidget, 1)
        self.setLayout(layout)

    def __createMainWidget(self, *widgets) -> qt.QWidget:
        mainWidget = qt.QSplitter(self)
        for widget in widgets:
            mainWidget.addWidget(widget)
        mainWidget.setStretchFactor(1, 1)
        for i in range(len(widgets)):
            mainWidget.setCollapsible(i, False)
        return mainWidget

    def __createTreeModel(self, treeview: Hdf5TreeView) -> NexusSortFilterProxyModel:
        treeModel = Hdf5TreeModel(treeview, ownFiles=False)
        treeModel.sigH5pyObjectLoaded.connect(self.__h5FileLoaded)
        treeModel.sigH5pyObjectRemoved.connect(self.__h5FileRemoved)
        treeModel.sigH5pyObjectSynchronized.connect(self.__h5FileSynchronized)
        treeModel.setDatasetDragEnabled(True)

        treeModelSorted = NexusSortFilterProxyModel(treeview)
        treeModelSorted.setSourceModel(treeModel)
        treeModelSorted.sort(0, qt.Qt.AscendingOrder)
        treeModelSorted.setSortCaseSensitivity(qt.Qt.CaseInsensitive)
        treeview.setModel(treeModelSorted)
        return treeModelSorted

    def __customizeTreeModelColumns(self):
        treeModel = self.__treeview.findHdf5TreeModel()
        columns = list(treeModel.COLUMN_IDS)
        columns.remove(treeModel.VALUE_COLUMN)
        columns.remove(treeModel.NODE_COLUMN)
        columns.remove(treeModel.DESCRIPTION_COLUMN)
        columns.insert(1, treeModel.DESCRIPTION_COLUMN)
        self.__treeview.header().setSections(columns)

    def __createTreeWindow(self, treeView: Hdf5TreeView) -> qt.QWidget:
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

        widget = qt.QWidget(self)
        layout = qt.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(toolbar)
        layout.addWidget(treeView)
        return widget

    def __iterModelIndices(
        self, max_depth: Optional[int] = None, indexes: Optional[Sequence] = None
    ) -> Iterator[Tuple[Tuple[qt.QModelIndex, int], qt.QModelIndex, int]]:
        selection = self.__treeview.selectionModel()
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
        model = self.__treeview.model()
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

            model = self.__treeview.findHdf5TreeModel()
            for h5 in h5files:
                model.removeH5pyObject(h5)

    def __refreshSelected(self):
        """Refresh all selected items"""
        model = self.__treeview.model()
        selection = self.__treeview.selectionModel()
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
        model = self.__treeview.findHdf5TreeModel()
        # This is buggy right now while h5py do not allow to close a file
        # while references are still used.
        # FIXME: The architecture have to be reworked to support this feature.
        # model.synchronizeH5pyObject(h5)

        if filename is None:
            filename = f"{h5.file.filename}::{h5.name}"
        row = model.h5pyObjectRow(h5)
        index = self.__treeview.model().index(row, 0, qt.QModelIndex())
        paths = self.__getPathFromExpandedNodes(self.__treeview, index)
        model.removeH5pyObject(h5)
        model.insertFile(filename, row)
        index = self.__treeview.model().index(row, 0, qt.QModelIndex())
        self.__expandNodesFromPaths(self.__treeview, index, paths)

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
        model = self.__treeview.model()
        for indexes, index, depth in self.__iterModelIndices(max_depth=2):
            if not model.hasChildren(index):
                continue
            self.__treeview.setExpanded(index, expanded)
            for row in range(model.rowCount(index)):
                childIndex = model.index(row, 0, index)
                indexes.append((childIndex, depth + 1))

    def __h5FileLoaded(self, loadedH5):
        self._h5files.append(loadedH5)
        self.displayData(loadedH5)

    def __h5FileRemoved(self, removedH5):
        data = self.__dataPanel.data()
        if data is not None:
            if data.file is not None:
                if data.file.filename == removedH5.file.filename:
                    self.__dataPanel.setData(None)
        removedH5.close()
        self._h5files.remove(removedH5)

    def __h5FileSynchronized(self, removedH5, loadedH5):
        data = self.__dataPanel.data()
        if data is not None:
            if data.file is not None:
                if data.file.filename == removedH5.file.filename:
                    try:
                        newData = loadedH5[data.name]
                        self.__dataPanel.setData(newData)
                    except Exception:
                        _logger.debug("Cannot synchronize", exc_info=True)
        removedH5.close()
        self._h5files.remove(removedH5)

    def closeEvent(self, event):
        self.displayData(None)
        self.closeAll()

    def closeAll(self):
        """Close all currently opened files"""
        self.__treeview.findHdf5TreeModel().clear()

    def __getFileObject(self, filename):
        for h5file in self._h5files:
            if h5file.filename == filename:
                return h5file

    def closeFile(self, filename):
        h5file = self.__getFileObject(filename)
        model = self.__treeview.findHdf5TreeModel()
        model.removeH5pyObject(h5file)

    def updateFile(self, filename):
        if not os.path.exists(filename):
            return
        h5file = self.__getFileObject(filename)
        if h5file is not None:
            self.__refreshAction.trigger()
            return
        self.closeFile(filename)
        model = self.__treeview.findHdf5TreeModel()
        h5file = h5py.File(filename, mode="a")
        try:
            model.sigH5pyObjectLoaded.emit(h5file, filename)
        except TypeError:
            # Support silx<2.0.0
            model.sigH5pyObjectLoaded.emit(h5file)
        model.insertH5pyObject(h5file, filename=filename)

    def setContentSorted(self, sort):
        """Set whether file content should be sorted or not.

        :param bool sort:
        """
        sort = bool(sort)
        if sort != self.isContentSorted():
            # save expanded nodes
            pathss = []
            root = qt.QModelIndex()
            model = self.__treeview.model()
            for i in range(model.rowCount(root)):
                index = model.index(i, 0, root)
                paths = self.__getPathFromExpandedNodes(self.__treeview, index)
                pathss.append(paths)

            self.__treeview.setModel(
                self.__treeModelSorted if sort else self.__treeModelSorted.sourceModel()
            )
            self._sortContentAction.setChecked(self.isContentSorted())

            # restore expanded nodes
            model = self.__treeview.model()
            for i in range(model.rowCount(root)):
                index = model.index(i, 0, root)
                paths = pathss.pop(0)
                self.__expandNodesFromPaths(self.__treeview, index, paths)

    def isContentSorted(self):
        """Returns whether the file content is sorted or not.

        :rtype: bool
        """
        return self.__treeview.model() is self.__treeModelSorted

    def displaySelectedData(self):
        """Called to update the dataviewer with the selected data."""
        selected = list(self.__treeview.selectedH5Nodes(ignoreBrokenLinks=False))
        if len(selected) == 1:
            # Update the viewer for one selection
            data = selected[0]
            self.__dataPanel.setData(data)
        else:
            _logger.debug("Too many data selected")

    def displayData(self, data):
        """Called to update the dataviewer with specific data."""
        self.__dataPanel.setData(data)

    def treeContextMenu(self, event: Hdf5ContextMenuEvent):
        """Called to populate the context menu"""
        selectedObjects = event.source().selectedH5Nodes(ignoreBrokenLinks=False)
        menu = event.menu()

        if not menu.isEmpty():
            menu.addSeparator()

        for obj in selectedObjects:
            h5 = obj.h5py_object

            name = obj.name
            if name.startswith("/"):
                name = name[1:]
            if name == "":
                name = "the root"

            action = qt.QAction("Show %s" % name, event.source())
            action.triggered.connect(lambda: self.displayData(h5))
            menu.addAction(action)

            if silx.io.is_file(h5):
                action = qt.QAction("Close %s" % obj.local_filename, event.source())
                action.triggered.connect(
                    lambda: self.__treeview.findHdf5TreeModel().removeH5pyObject(h5)
                )
                menu.addAction(action)
                action = qt.QAction(
                    "Synchronize %s" % obj.local_filename, event.source()
                )
                action.triggered.connect(lambda: self.__synchronizeH5pyObject(h5))
                menu.addAction(action)
