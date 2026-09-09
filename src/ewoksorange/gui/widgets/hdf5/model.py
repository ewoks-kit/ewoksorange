import os
from types import MappingProxyType
from typing import Any
from typing import Callable
from typing import Dict
from typing import Mapping
from typing import Optional

from silx.gui import icons
from silx.gui import qt
from silx.gui.hdf5 import Hdf5TreeModel as _SilxHdf5TreeModel
from silx.gui.hdf5.Hdf5Item import Hdf5Item
from silx.gui.hdf5.Hdf5LoadingItem import Hdf5LoadingItem
from silx.gui.hdf5.Hdf5Node import Hdf5Node
from silx.gui.hdf5.Hdf5TreeModel import LoadingItemRunnable
from silx.gui.hdf5.Hdf5TreeModel import _createRootLabel

from ....io.hdf5.static import StaticFile
from ....io.hdf5.utils import FileFactory
from ....io.hdf5.utils import FileType


class Hdf5TreeModel(_SilxHdf5TreeModel):
    """Tree model which opens every file with `fileClass`.

    :param fileClass: Called as ``fileClass(filename, **fileArguments)`` and
        returns an h5py-like object. The access classes of
        :mod:`ewoksorange.io.hdf5` implement the access regimes, and
        :class:`h5py.File` can be given as well.
    :param parent: Qt parent of the model.
    :param backgroundLoading: Read files in a worker thread instead of
        blocking the GUI, showing a loading item until the file is read. It is
        off by default: HDF5 refuses handles with conflicting locking flags, so
        reading a file in a worker thread races with the current process
        writing that same file.
    :param fileArguments: The arguments `fileClass` takes besides the file
        name, for example ``mode``, ``keep_open`` or ``retry_timeout``. Which
        of them exist is up to `fileClass`.

    SILX DIFFERENCE with :class:`silx.gui.hdf5.Hdf5TreeModel`: files are opened
    by `fileClass` instead of :func:`silx.io.open`.
    """

    sigFileFailed = qt.Signal(str, object)
    """Emitted with the file name and the exception when a file cannot be read."""

    def __init__(
        self,
        fileClass: FileFactory = StaticFile,
        parent: Optional[qt.QObject] = None,
        backgroundLoading: bool = False,
        **fileArguments: Any,
    ) -> None:
        # ownFiles=False: the tree viewer owns the file life cycle.
        super().__init__(parent, ownFiles=False)
        self._fileClass = fileClass
        self._backgroundLoading = backgroundLoading
        self._file_arguments: Dict[str, Any] = dict(fileArguments)

    @property
    def fileClass(self) -> FileFactory:
        """The class files are opened with."""
        return self._fileClass

    @property
    def fileArguments(self) -> Mapping[str, Any]:
        """The arguments :attr:`fileClass` is called with."""
        return MappingProxyType(self._file_arguments)

    @property
    def backgroundLoading(self) -> bool:
        """Whether files are read in a worker thread."""
        return self._backgroundLoading

    def openFile(self, filename: str) -> FileType:
        """Return an h5py-like object for `filename`."""
        return self._fileClass(filename, **self._file_arguments)

    def exists(self, filename: str) -> bool:
        """Return whether `filename` can be opened by :meth:`openFile`."""
        return os.path.exists(filename)

    def insertFile(self, filename: str, row: int = -1) -> None:
        """Add `filename` to the tree, as a broken item when it cannot be read.

        SILX DIFFERENCE with :meth:`silx.gui.hdf5.Hdf5TreeModel.insertFile`,
        which opens the file with :func:`silx.io.open` and raises when it
        cannot be read. Showing data must not make the caller fail, and a file
        which is not in the tree at all is indistinguishable from one nobody
        asked for.
        """
        try:
            h5file = self.openFile(filename)
        except Exception as e:  # shown in the tree instead of raising
            self._insertBrokenFile(filename, e, row=row)
            return
        try:
            self.sigH5pyObjectLoaded.emit(h5file, filename)
        except TypeError:
            # Support silx<2.0.0
            self.sigH5pyObjectLoaded.emit(h5file)
        try:
            self.insertH5pyObject(h5file, row=row, filename=filename)
        except TypeError:
            # Support silx<2.0.0
            self.insertH5pyObject(h5file, row=row)

    def insertFileAsync(
        self,
        filename: str,
        row: int = -1,
        synchronizingNode: Optional[Hdf5Node] = None,
    ) -> None:
        """Add `filename` to the tree, in a worker thread when
        :attr:`backgroundLoading` is set.

        A loading item is shown until the file is read, unless
        `synchronizingNode` is given, which is replaced instead.

        SILX DIFFERENCE with :meth:`silx.gui.hdf5.Hdf5TreeModel.insertFileAsync`:
        the file is opened with :meth:`openFile` instead of
        :func:`silx.io.open`, only in a worker thread when
        :attr:`backgroundLoading` is set, and it exists according to
        :meth:`exists` instead of :func:`os.path.isfile`, which a name
        refreshed through `synchronizingNode` does not have to be.
        """
        if synchronizingNode is None:
            if not self.exists(filename):
                raise OSError(f"Filename '{filename}' must be a file path")
            item = Hdf5LoadingItem(
                text=os.path.basename(filename),
                parent=self.nodeFromIndex(qt.QModelIndex()),
                animatedIcon=icons.getWaitIcon(),
                openedPath=filename,
            )
            self.insertNode(row, item)
        else:
            item = synchronizingNode

        runnable = _OpenFileRunnable(
            filename, item, self.openFile, populateAll=self._backgroundLoading
        )
        runnable.fileFailed.connect(self.sigFileFailed)
        runnable.itemReady.connect(_silxPrivate(self, "itemReady"))
        runnable.runnerFinished.connect(_silxPrivate(self, "releaseRunner"))
        _silxPrivate(self, "runnerSet").add(runnable)
        if self._backgroundLoading:
            qt.silxGlobalThreadPool().start(runnable)
        else:
            runnable.run()

    def _insertBrokenFile(self, filename: str, error: Exception, row: int = -1) -> None:
        """Add an item showing that `filename` could not be read, and report it."""
        self.insertNode(
            row,
            _BrokenFileItem(filename, error, self.nodeFromIndex(qt.QModelIndex())),
        )
        self.sigFileFailed.emit(filename, error)


def _silxPrivate(model: _SilxHdf5TreeModel, name: str):
    """Return a name-mangled member of :class:`silx.gui.hdf5.Hdf5TreeModel`.

    SILX DIFFERENCE: silx offers no public way to hand a loaded item back to
    the model, so `__itemReady`, `__releaseRunner` and `__runnerSet` are used
    directly. `__itemReady` replaces the loading item and emits
    `sigH5pyObjectLoaded` or `sigH5pyObjectSynchronized`.
    """
    return getattr(model, f"_{_SilxHdf5TreeModel.__name__}__{name}")


class _OpenFileRunnable(LoadingItemRunnable):
    """Runnable which opens a file with a given callable.

    SILX DIFFERENCE with ``silx.gui.hdf5.Hdf5TreeModel.LoadingItemRunnable``,
    which opens the file with :func:`silx.io.open`, always reads the whole tree
    and only survives an `OSError`, after which the file is dropped from the
    tree. A file which cannot be read must not stop the canvas, so every
    exception is reported and the file stays in the tree as a broken item.
    """

    class _Signals(qt.QObject):
        fileFailed = qt.Signal(str, object)

    def __init__(
        self,
        filename: str,
        item: Hdf5Node,
        openFile: Callable,
        populateAll: bool = True,
    ) -> None:
        super().__init__(filename, item)
        self._openFile = openFile
        # Reading the whole tree up front is what makes loading worth a thread.
        # In the GUI thread it holds the file open far longer than needed.
        self._populateAll = populateAll
        self._signals = self._Signals()

    @property
    def fileFailed(self) -> qt.Signal:
        """Emitted with the file name and the exception when a file fails."""
        return self._signals.fileFailed

    def run(self) -> None:
        h5file = None
        error = None
        try:
            h5file = self._openFile(self.filename)
            newItem = Hdf5Item(
                text=_createRootLabel(h5file),
                obj=h5file,
                parent=self.oldItem.parent,
                populateAll=self._populateAll,
                openedPath=self.oldItem._openedPath,
            )
        except Exception as e:  # shown in the tree instead of raising
            error = e
            newItem = _BrokenFileItem(self.filename, e, self.oldItem.parent)
            if h5file is not None:
                h5file.close()
        # No error for the model of silx: it drops the item when one is given.
        self.itemReady.emit(self.oldItem, newItem, None, self.filename)
        if error is not None:
            self.fileFailed.emit(self.filename, error)
        self.runnerFinished.emit(self)


class _BrokenFileItem(Hdf5Item):
    """A file which could not be read, shown with a broken icon and the reason.

    SILX DIFFERENCE: silx shows both for an item it fails to reach while
    populating a tree, but offers no way to say it about an item created here,
    so `__error` is set directly. An object of `None` without an HDF5 class is
    what makes the item broken. Its description tooltip is taken over because
    silx reads it through the object of the parent, which the root of the tree
    does not have.
    """

    def __init__(self, filename: str, error: Exception, parent: Hdf5Node) -> None:
        super().__init__(
            text=os.path.basename(filename),
            obj=None,
            parent=parent,
            openedPath=filename,
        )
        self._Hdf5Item__error = f"{filename} cannot be read. {error}"

    def dataDescription(self, role):
        if role == qt.Qt.ToolTipRole:
            return self._Hdf5Item__error
        return super().dataDescription(role)
