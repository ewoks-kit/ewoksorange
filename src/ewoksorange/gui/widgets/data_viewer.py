import logging
import sys
from typing import Optional

from silx.gui import qt
from silx.gui.data.DataViewerFrame import DataViewerFrame
from silx.gui.hdf5 import Hdf5ContextMenuEvent

from .hdf5_tree_viewer import Hdf5TreeViewer

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

    Other tree operations are reached through the `treeViewer` property,
    for example `viewer.treeViewer.setContentSorted(False)`.
    """

    def __init__(self, parent, *, mode: str = "a", locking: Optional[bool] = None):
        super().__init__(parent)

        # Do we need buttons for these?
        # silx.config.DEFAULT_PLOT_IMAGE_Y_AXIS_ORIENTATION = "downward"
        # silx.config.DEFAULT_PLOT_IMAGE_Y_AXIS_ORIENTATION = "upward"
        # silx.config.DEFAULT_PLOT_BACKEND = "matplotlib"
        # silx.config.DEFAULT_PLOT_BACKEND = "opengl"

        self.__treeViewer = Hdf5TreeViewer(
            self, mode=mode, locking=locking, toolbar=True
        )
        self.__dataPanel = DataViewerFrame(self)

        self.__mainWidget = self.__createMainWidget(self.__treeViewer, self.__dataPanel)

        self.__setLayout(self.__mainWidget)

        self.__treeViewer.sigH5FileLoaded.connect(self.displayData)
        self.__treeViewer.sigH5FileRemoved.connect(self.__h5FileRemoved)
        self.__treeViewer.sigH5FileSynchronized.connect(self.__h5FileSynchronized)
        self.__treeViewer.sigSelectionActivated.connect(self.displaySelectedData)
        self.__treeViewer.addContextMenuCallback(self.treeContextMenu)

    @property
    def treeViewer(self) -> Hdf5TreeViewer:
        """The tree of open files on the left side."""
        return self.__treeViewer

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

    def __h5FileRemoved(self, removedH5):
        data = self.__dataPanel.data()
        if data is not None:
            if data.file is not None:
                if data.file.filename == removedH5.file.filename:
                    self.__dataPanel.setData(None)

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

    def closeEvent(self, event):
        self.displayData(None)
        self.closeAll()

    def closeAll(self):
        """Close all currently opened files"""
        self.__treeViewer.closeAll()

    def closeFile(self, filename):
        self.__treeViewer.closeFile(filename)

    def updateFile(self, filename):
        self.__treeViewer.updateFile(filename)

    def setContentSorted(self, sort):
        """Set whether file content should be sorted."""
        self.__treeViewer.setContentSorted(sort)

    def isContentSorted(self):
        """Return whether file content is sorted."""
        return self.__treeViewer.isContentSorted()

    def displaySelectedData(self):
        """Called to update the dataviewer with the selected data."""
        selected = list(self.__treeViewer.selectedH5Nodes(ignoreBrokenLinks=False))
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


def main(argv=None) -> int:
    """Show a data viewer for the files given on the command line.

    Args:
        argv: Command line arguments. Defaults to `sys.argv[1:]`.

    Returns:
        The exit code of the Qt application.
    """
    if argv is None:
        argv = sys.argv[1:]

    app = qt.QApplication([])
    viewer = DataViewer(None)
    viewer.setWindowTitle("Ewoks data viewer")
    viewer.resize(1000, 600)
    for filename in argv:
        viewer.updateFile(filename)
    viewer.setVisible(True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
