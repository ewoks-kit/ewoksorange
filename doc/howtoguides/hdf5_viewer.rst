.. _How to browse HDF5 data ?:

How to browse HDF5 data ?
=========================

In short
--------

Put a viewer in the main area of an Orange widget, and give it a
:term:`tree model` holding the :term:`access class` for the files it will show:

.. code-block:: python

    from ewoksorange.gui.widgets.hdf5.model import Hdf5TreeModel
    from ewoksorange.gui.widgets.hdf5.viewer import Hdf5Viewer
    from ewoksorange.io.hdf5.owned import OwnedFile

    viewer = Hdf5Viewer(Hdf5TreeModel(OwnedFile), self.mainArea)
    viewer.updateFile("/path/to/result.h5")

Pick the class from who may write the file while it is being browsed:

.. list-table::
    :header-rows: 1
    :widths: 30 34 36

    * - The file
      - Access class
      - What it does
    * - :term:`Nobody writes it <Static file>`
      - ``StaticFile`` (the default)
      - keeps the file open, read-only and unlocked
    * - :term:`Another process writes it <Externally written file>`
      - ``LiveFile``
      - reads it unlocked so a writer is never blocked nor refused the file,
        and reopens it on every read so a read can see more than the previous
        one
    * - :term:`A task of this process may write it <Owned file>`
      - ``OwnedFile``
      - reads it read-write, which a task of this process can join whenever it
        opens the file, and reads its external links read-only and unlocked

That choice is the only one which needs thought, and :ref:`hdf5_access`
explains why it is the file and not the widget which determines it. Everything
below is detail: the widgets, what else the model takes, and how to extend it.

To try it out without writing any code:

.. code-block:: bash

    python3 -m ewoksorange.gui.widgets.hdf5 --demo

The widgets
-----------

:mod:`ewoksorange.gui.widgets.hdf5` provides two widgets to browse files
supported by :term:`silx`:

* :class:`~ewoksorange.gui.widgets.hdf5.viewer.Hdf5Viewer`: a file tree next to
  a data panel (a :class:`~silx.gui.data.DataViewerFrame.DataViewerFrame`).
* :class:`~ewoksorange.gui.widgets.hdf5.tree_viewer.Hdf5TreeViewer`: the file
  tree on its own (a :class:`~silx.gui.hdf5.Hdf5TreeView` with a toolbar).

Both are plain ``QWidget`` instances, and neither of them decides how a file is
opened: they take a :class:`~ewoksorange.gui.widgets.hdf5.model.Hdf5TreeModel`
which opens every file with its access class.

.. code-block:: python

    class MyWidget(OWEwoksWidgetOneThread, **kwargs):
        def _init_main_area(self):
            super()._init_main_area()
            layout = self._get_main_layout()

            self._viewer = Hdf5Viewer(Hdf5TreeModel(OwnedFile), self.mainArea)
            layout.addWidget(self._viewer)
            layout.setStretchFactor(self._viewer, 1)

        def task_output_changed(self):
            self._viewer.updateFile("/path/to/result.h5")

        def closeEvent(self, event):
            self._viewer.closeEvent(event)

:meth:`~ewoksorange.gui.widgets.hdf5.viewer.Hdf5Viewer.updateFile` opens the
file, or refreshes it when it is already open, and ignores a file which does not
exist yet, so a widget can call it before its task has written anything.
:meth:`~ewoksorange.gui.widgets.hdf5.viewer.Hdf5Viewer.closeFile` and
:meth:`~ewoksorange.gui.widgets.hdf5.viewer.Hdf5Viewer.closeAll` close them
again.

The data panel stays empty until a node is picked in the tree. Pass
``displayOnLoad=True`` to show a file as soon as it is opened, at the cost of
the reads the data panel needs to choose how to show it, which delay a writer
of that file in this process.

For the tree on its own:

.. code-block:: python

    from ewoksorange.gui.widgets.hdf5.tree_viewer import Hdf5TreeViewer

    tree = Hdf5TreeViewer(Hdf5TreeModel(), parent, toolbar=True)
    tree.updateFile("/path/to/result.h5")

The toolbar holds the refresh, close, expand, collapse and sort actions. It is
hidden by default and its keyboard shortcuts stay active while it is hidden.
Connect to
:attr:`~ewoksorange.gui.widgets.hdf5.tree_viewer.Hdf5TreeViewer.sigSelectionActivated`,
:attr:`~ewoksorange.gui.widgets.hdf5.tree_viewer.Hdf5TreeViewer.sigH5FileLoaded`,
:attr:`~ewoksorange.gui.widgets.hdf5.tree_viewer.Hdf5TreeViewer.sigH5FileRemoved`
or
:attr:`~ewoksorange.gui.widgets.hdf5.tree_viewer.Hdf5TreeViewer.sigH5FileSynchronized`
to react to the tree content.

What else the model takes
-------------------------

Every keyword the model does not use itself is passed on to the access class,
so the retry options of :class:`~ewoksorange.io.hdf5.live.LiveFile` are given
to the model:

.. code-block:: python

    model = Hdf5TreeModel(LiveFile, retry_timeout=5, retry_period=0.1)

.. dropdown:: Retrying a read of a file being written

    A file another process is writing shows everything that writer has
    flushed, so refreshing follows an acquisition. Groups are read when they
    are first expanded, so a group opened for the first time shows what has
    been added to it since, while one opened earlier shows what it held then,
    until the file is refreshed. A read landing midway through a flush fails,
    so pass ``retry_timeout`` in seconds to retry it and ``retry_period`` in
    seconds to wait between retries. See :ref:`hdf5_access`.

.. dropdown:: Reading files without blocking the GUI

    Files are read in the GUI thread. Pass ``backgroundLoading=True`` to the
    model to read them in a worker thread instead, showing a loading item
    rather than blocking. It is off by default because a worker thread reading
    a file races with this process writing that same file. With it on, a file
    is not in the tree yet when ``updateFile`` returns;
    :meth:`~ewoksorange.gui.widgets.hdf5.viewer.Hdf5Viewer.waitForLoading`
    waits for it.

.. dropdown:: Browsing with h5py itself

    The access class is anything which takes a file name and returns an
    h5py-like object, so :class:`h5py.File` can be given as well, for a file
    nothing else touches:

    .. code-block:: python

        model = Hdf5TreeModel(h5py.File, mode="r", locking=False)

    The classes of :mod:`ewoksorange.io.hdf5` read through the
    :mod:`silx.io.commonh5` API instead, so they never write the file they
    show, whatever mode it was opened with.

Telling the user a file could not be read
-----------------------------------------

A widget always absorbs read failures: raising would leave the
:term:`Orange canvas` with a dialog per refresh. A file which cannot be read
stays in the tree instead, with a broken icon and the reason in its tooltip, so
that a refresh can be tried once the writer is done; the parts of a file which
cannot be read are skipped the same way.

That leaves the user looking at less than the file holds, so say so in the
widget as well:

.. code-block:: python

    self._viewer.treeViewer.sigFileFailed.connect(
        lambda filename, error: self.setStatusMessage(f"Cannot read {filename}")
    )

Outside a widget the :term:`reading policy` is a choice, and
:func:`~ewoksorange.io.hdf5.access.read_access` is the helper for a task
reading a file which is being written:

.. code-block:: python

    from ewoksorange.io.hdf5.access import read_access

    with read_access("being_written.h5", retry_timeout=10) as h5file:
        values = h5file["entry/measurement/diode"][()]

Reading such a file faithfully means retrying, since a failure normally says
the writer is midway through a write rather than that the data is missing. A
file this process writes is never seen half-written, so nothing needs retrying
there.

Custom actions in the tree context menu
---------------------------------------

Register a callback with
:meth:`~ewoksorange.gui.widgets.hdf5.tree_viewer.Hdf5TreeViewer.addContextMenuCallback`.
It receives a :class:`~silx.gui.hdf5.Hdf5ContextMenuEvent` for the node under
the cursor, from which ``menu()`` gives the ``QMenu`` to populate and
``source()`` the tree view. Each selected node is a
:class:`~silx.gui.hdf5.H5Node`, so :func:`~ewoksorange.io.hdf5.utils.is_group`
and :func:`~ewoksorange.io.hdf5.utils.is_dataset` tell groups and datasets
apart:

.. code-block:: python

    from ewoksorange.io.hdf5.utils import is_dataset
    from silx.gui import qt

    def addPrintAction(event):
        menu = event.menu()
        if not menu.isEmpty():
            menu.addSeparator()

        for node in event.source().selectedH5Nodes(ignoreBrokenLinks=False):
            if not is_dataset(node.h5py_object):
                continue
            action = qt.QAction(f"Print {node.name}", event.source())
            action.triggered.connect(
                lambda checked=False, node=node: print(node.h5py_object[()])
            )
            menu.addAction(action)

    viewer.treeViewer.addContextMenuCallback(addPrintAction)

Bind ``node`` as a default argument as shown above: without it every action
would use the last node of the loop.

``python3 -m ewoksorange.gui.widgets.hdf5 --demo`` adds one action for groups
and one for datasets, both opening a ``QMessageBox``.

Supporting another regime
-------------------------

A regime the classes above do not cover is a matter of subclassing
:class:`~ewoksorange.io.hdf5.base.Hdf5File` and overriding how it opens files:

.. code-block:: python

    from ewoksorange.io.hdf5.base import Hdf5File

    class MyFile(Hdf5File):
        def open_h5_file(self, filename, **open_options):
            return MyH5pyFileContextManager(filename, **open_options)

    model = Hdf5TreeModel(MyFile, mode="r")

:meth:`~ewoksorange.io.hdf5.base.Hdf5File.open_external_h5_file` does the same
for the files external links point at, which is what lets a file and its links
be opened differently.

.. dropdown:: Browsing content which is not on disk

    Override :meth:`~ewoksorange.gui.widgets.hdf5.model.Hdf5TreeModel.exists`
    as well when a file name does not refer to a path on disk:

    .. code-block:: python

        from silx.io import commonh5

        class MemoryFile(commonh5.File):
            def __init__(self, name, contents):
                super().__init__(name, mode="r")
                self.add_node(commonh5.Dataset("data", contents[name]))

        class MemoryTreeModel(Hdf5TreeModel):
            def __init__(self, contents, parent=None):
                super().__init__(MemoryFile, parent, contents=contents)
                self.contents = contents

            def exists(self, filename):
                return filename in self.contents

    Any :class:`silx.io.commonh5.File` will do: the access classes of
    :mod:`ewoksorange.io.hdf5` are such subclasses themselves.

The classes in :mod:`ewoksorange.io.hdf5` need no GUI, so they can be used on
their own as well:

.. code-block:: python

    from ewoksorange.io.hdf5.live import LiveFile

    with LiveFile("being_written.h5", retry_timeout=5) as h5file:
        values = h5file["entry/measurement/diode"][()]

Types and predicates
--------------------

:mod:`ewoksorange.io.hdf5.utils` tells the HDF5 object kinds apart, whichever
of the classes above an object comes from, and names them for annotations:

.. code-block:: python

    from ewoksorange.io.hdf5.utils import GroupType, is_dataset, is_group

    def iter_datasets(group: GroupType):
        for name in group:
            item = group[name]
            if is_dataset(item):
                yield item
            elif is_group(item):
                yield from iter_datasets(item)

:func:`~ewoksorange.io.hdf5.utils.is_group` is true for a file as well, like
:mod:`silx.io` and :term:`h5py`.
