import abc
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

from .....io.hdf5.utils import FileType

# Qt classes have a binding-specific metaclass which abc.ABCMeta must extend.
_QtABCMeta = type("_QtABCMeta", (type(qt.QObject), abc.ABCMeta), {})


class Hdf5TreeModel(_SilxHdf5TreeModel, metaclass=_QtABCMeta):
    """Tree model which opens every file through :meth:`openFile`.

    SILX DIFFERENCE with :class:`silx.gui.hdf5.Hdf5TreeModel`: files are opened
    by :meth:`openFile` instead of :func:`silx.io.open`.
    """

    DEFAULT_OPEN_OPTIONS: Mapping[str, Any] = MappingProxyType({})
    """Options completing the ones provided at instantiation."""

    BACKGROUND_LOADING: bool = False
    """Read files in a worker thread instead of blocking the GUI.

    Off by default: HDF5 refuses handles with conflicting locking flags, so
    reading a file in a worker thread races with the current process writing
    that same file.
    """

    def __init__(self, parent: Optional[qt.QObject] = None, **open_options) -> None:
        # ownFiles=False: the tree viewer owns the file life cycle.
        super().__init__(parent, ownFiles=False)
        self._open_options: Dict[str, Any] = {
            **self.DEFAULT_OPEN_OPTIONS,
            **open_options,
        }

    @property
    def openOptions(self) -> Mapping[str, Any]:
        """The options used to open files."""
        return MappingProxyType(self._open_options)

    @abc.abstractmethod
    def openFile(self, filename: str) -> FileType:
        """Return an h5py-like object for `filename`."""

    def exists(self, filename: str) -> bool:
        """Return whether `filename` can be opened by :meth:`openFile`."""
        return os.path.exists(filename)

    def insertFile(self, filename: str, row: int = -1) -> None:
        """Add `filename` to the tree.

        SILX DIFFERENCE with :meth:`silx.gui.hdf5.Hdf5TreeModel.insertFile`,
        which opens the file with :func:`silx.io.open`.
        """
        h5file = self.openFile(filename)
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
        :attr:`BACKGROUND_LOADING` is set.

        A loading item is shown until the file is read, unless
        `synchronizingNode` is given, which is replaced instead.

        SILX DIFFERENCE with :meth:`silx.gui.hdf5.Hdf5TreeModel.insertFileAsync`:
        the file is opened with :meth:`openFile` instead of
        :func:`silx.io.open`, and only in a worker thread when
        :attr:`BACKGROUND_LOADING` is set.
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
            filename, item, self.openFile, populateAll=self.BACKGROUND_LOADING
        )
        runnable.itemReady.connect(_silxPrivate(self, "itemReady"))
        runnable.runnerFinished.connect(_silxPrivate(self, "releaseRunner"))
        _silxPrivate(self, "runnerSet").add(runnable)
        if self.BACKGROUND_LOADING:
            qt.silxGlobalThreadPool().start(runnable)
        else:
            runnable.run()


def _silxPrivate(model: _SilxHdf5TreeModel, name: str):
    """Return a name-mangled member of :class:`silx.gui.hdf5.Hdf5TreeModel`.

    SILX DIFFERENCE: silx offers no public way to hand a loaded item back to
    the model, so `__itemReady`, `__releaseRunner` and `__runnerSet` are used
    directly. `__itemReady` replaces the loading item and emits
    `sigH5pyObjectLoaded` or `sigH5pyObjectSynchronized`.
    """
    return getattr(model, f"_{_SilxHdf5TreeModel.__name__}__{name}")


class _OpenFileRunnable(LoadingItemRunnable):
    """Runnable which opens a file with a given callable."""

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

    def run(self) -> None:
        h5file = None
        try:
            h5file = self._openFile(self.filename)
            newItem = Hdf5Item(
                text=_createRootLabel(h5file),
                obj=h5file,
                parent=self.oldItem.parent,
                populateAll=self._populateAll,
                openedPath=self.oldItem._openedPath,
            )
            error = None
        except Exception as e:  # reported to the model through itemReady
            error = e
            newItem = None
            if h5file is not None:
                h5file.close()
        self.itemReady.emit(self.oldItem, newItem, error, self.filename)
        self.runnerFinished.emit(self)
