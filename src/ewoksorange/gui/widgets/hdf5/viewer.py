import logging
from typing import Optional

from silx.gui import qt
from silx.gui.data.DataViewerFrame import DataViewerFrame
from silx.gui.hdf5 import Hdf5ContextMenuEvent

from ....io.hdf5.utils import FileType
from .model.base import Hdf5TreeModel
from .tree_viewer import Hdf5TreeViewer

_logger = logging.getLogger(__name__)


class Hdf5Viewer(qt.QWidget):
    """Browse data from files supported by silx.

    `model` decides which files can be browsed and how they are opened.

    `displayOnLoad` shows a file in the data panel as soon as it is opened.
    It is off by default, like in `silx view`: the data panel reads the file to
    choose how to show it, which is wasted on a file the user did not ask to
    see and which delays a writer of that file in this process.

    An embeddable equivalent of the `silx view` application
    (``silx.app.view.Viewer``), composing :class:`Hdf5TreeViewer` with
    :class:`silx.gui.data.DataViewerFrame.DataViewerFrame`. It has none of the
    application features of `silx view`: no menu bar, no settings, no custom
    NXdata panel, and no plot backend or axis orientation actions (those set
    process-wide :mod:`silx.config` values).
    """

    def __init__(
        self,
        model: Hdf5TreeModel,
        parent: Optional[qt.QWidget] = None,
        *,
        displayOnLoad: bool = False,
    ) -> None:
        super().__init__(parent)

        self.__treeViewer = Hdf5TreeViewer(model, self, toolbar=True)
        self.__dataPanel = DataViewerFrame(self)

        self.__mainWidget = self.__createMainWidget(self.__treeViewer, self.__dataPanel)

        self.__setLayout(self.__mainWidget)

        if displayOnLoad:
            self.__treeViewer.sigH5FileLoaded.connect(self.displayData)
        self.__treeViewer.sigH5FileRemoved.connect(self.__h5FileRemoved)
        self.__treeViewer.sigH5FileSynchronized.connect(self.__h5FileSynchronized)
        self.__treeViewer.sigSelectionActivated.connect(self.displaySelectedData)
        self.__treeViewer.addContextMenuCallback(self.treeContextMenu)

    @property
    def treeViewer(self) -> Hdf5TreeViewer:
        """The tree of open files on the left side."""
        return self.__treeViewer

    def __setLayout(self, mainWidget: qt.QWidget) -> None:
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

    def __h5FileRemoved(self, removedH5: FileType) -> None:
        data = self.__dataPanel.data()
        if data is not None:
            if data.file is not None:
                if data.file.filename == removedH5.file.filename:
                    self.__dataPanel.setData(None)

    def __h5FileSynchronized(self, removedH5: FileType, loadedH5: FileType) -> None:
        data = self.__dataPanel.data()
        if data is not None:
            if data.file is not None:
                if data.file.filename == removedH5.file.filename:
                    try:
                        newData = loadedH5[data.name]
                        self.__dataPanel.setData(newData)
                    except Exception:
                        _logger.debug("Cannot synchronize", exc_info=True)

    def closeEvent(self, event: qt.QCloseEvent) -> None:
        self.displayData(None)
        self.closeAll()

    def closeAll(self) -> None:
        """Close all currently opened files"""
        self.__treeViewer.closeAll()

    def waitForLoading(self, timeout: float = 60.0) -> None:
        """Wait until the files loading in the background are shown."""
        self.__treeViewer.waitForLoading(timeout)

    def closeFile(self, filename: str) -> None:
        self.__treeViewer.closeFile(filename)

    def updateFile(self, filename: str) -> None:
        self.__treeViewer.updateFile(filename)

    def setContentSorted(self, sort: bool) -> None:
        """Set whether file content should be sorted."""
        self.__treeViewer.setContentSorted(sort)

    def isContentSorted(self) -> bool:
        """Return whether file content is sorted."""
        return self.__treeViewer.isContentSorted()

    def displaySelectedData(self) -> None:
        """Display the data selected in the tree."""
        selected = list(self.__treeViewer.selectedH5Nodes(ignoreBrokenLinks=False))
        if len(selected) == 1:
            # Update the viewer for one selection
            data = selected[0]
            self.__dataPanel.setData(data)
        else:
            _logger.debug("Too many data selected")

    def displayData(self, data: Optional[FileType]) -> None:
        """Display `data` in the data panel."""
        self.__dataPanel.setData(data)

    def treeContextMenu(self, event: Hdf5ContextMenuEvent) -> None:
        """Populate the context menu of the tree."""
        selectedObjects = event.source().selectedH5Nodes(ignoreBrokenLinks=False)
        menu = event.menu()

        for obj in selectedObjects:
            h5 = obj.h5py_object

            name = obj.name
            if name.startswith("/"):
                name = name[1:]
            if name == "":
                name = "the root"

            action = qt.QAction("Show %s" % name, event.source())
            action.triggered.connect(lambda checked=False, h5=h5: self.displayData(h5))
            menu.addAction(action)
