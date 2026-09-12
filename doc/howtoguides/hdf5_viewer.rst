.. _How to browse HDF5 data ?:

How to browse HDF5 data ?
=========================

:mod:`ewoksorange.gui.widgets.hdf5` provides two widgets to browse files
supported by :term:`silx`:

* :class:`~ewoksorange.gui.widgets.hdf5.viewer.Hdf5Viewer`: a file tree next to
  a data panel (a :class:`~silx.gui.data.DataViewerFrame.DataViewerFrame`).
* :class:`~ewoksorange.gui.widgets.hdf5.tree_viewer.Hdf5TreeViewer`: the file
  tree on its own (a :class:`~silx.gui.hdf5.Hdf5TreeView` with a toolbar).

Both are plain ``QWidget`` instances, so they can be added to the main area of
an Orange widget. Neither of them decides how a file is opened: they take a
:term:`tree model` which does, and picking that model is the only choice that
needs thought.

To try the widgets without writing any code:

.. code-block:: bash

    python3 -m ewoksorange.gui.widgets.hdf5 --demo

Which model to use
------------------

Pick the model from the :term:`access regime` of the file, that is from who may
write it while it is being browsed. :ref:`hdf5_access` explains why this and not
the widget is what determines the mode a file is opened with.

.. list-table::
    :header-rows: 1
    :widths: 26 40 34

    * - The file
      - Model
      - What it does
    * - :term:`Nobody writes it <Static file>`
      - :class:`~ewoksorange.gui.widgets.hdf5.model.static.StaticFileTreeModel`
      - keeps the file open, read-only and unlocked
    * - :term:`Another process writes it <Externally written file>`
      - :class:`~ewoksorange.gui.widgets.hdf5.model.live.LiveFileTreeModel`
      - reads it unlocked so the writer is never blocked, and reopens it on
        every read so a read can see more than the previous one
    * - :term:`This process writes it <Owned file>`
      - :class:`~ewoksorange.gui.widgets.hdf5.model.owned.OwnedFileTreeModel`
      - reopens it, joining the mode this process already has
    * - This process writes it and it has
        :term:`external links <External link>`
      - :class:`~ewoksorange.gui.widgets.hdf5.model.owned.OwnedFileLinksTreeModel`
      - keeps it open, following links read-only and unlocked
    * - Its :term:`external links <External link>` need their own options
      - :class:`~ewoksorange.gui.widgets.hdf5.model.links.LinkAwareTreeModel`
      - keeps it open, links use ``set_external_access`` options

When in doubt, prefer a reopening model: a file which is only read while it is
open costs a little more per read and never stops anything else from writing.

A file another process is writing only shows what that writer has committed by
closing it, unless the writer uses :term:`SWMR`, so refreshing during an
acquisition advances between scans rather than continuously. See
:ref:`hdf5_access`.

``python3 -m ewoksorange.gui.widgets.hdf5 --access`` takes the same regimes on
the command line, so one can be tried on real data before it is wired into a
widget:

.. code-block:: bash

    python3 -m ewoksorange.gui.widgets.hdf5 --access owned results.h5

Reading policies
----------------

A widget always absorbs read failures: raising would leave the
:term:`Orange canvas` with a dialog per refresh. The models above therefore
show what is readable and skip what is not, and a
:term:`reading policy` only has to be chosen where a widget is not the reader.

Two things are worth knowing about that choice:

* Reading an :term:`externally written file` faithfully means retrying, since a
  failure normally says the writer is midway through a write rather than that
  the data is missing. :func:`~ewoksorange.io.hdf5.access.read_access` takes a
  ``retry_timeout`` for that, and :mod:`silx.io.h5py_utils` has the decorators
  it is built on.
* A file this process writes is never seen half-written, so nothing needs
  retrying there.

.. code-block:: python

    from ewoksorange.io.hdf5.access import read_access

    with read_access("being_written.h5", retry_timeout=10) as h5file:
        values = h5file["entry/measurement/diode"][()]

Using a viewer in a widget
--------------------------

.. code-block:: python

    from ewoksorange.gui.widgets.hdf5.model.live import OwnedFileTreeModel
    from ewoksorange.gui.widgets.hdf5.viewer import Hdf5Viewer

    class MyWidget(OWEwoksWidgetOneThread, **kwargs):
        def _init_main_area(self):
            super()._init_main_area()
            layout = self._get_main_layout()

            self._viewer = Hdf5Viewer(OwnedFileTreeModel(), self.mainArea)
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

    from ewoksorange.gui.widgets.hdf5.model.static import StaticFileTreeModel
    from ewoksorange.gui.widgets.hdf5.tree_viewer import Hdf5TreeViewer

    tree = Hdf5TreeViewer(StaticFileTreeModel(), parent, toolbar=True)
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

Files are read in the GUI thread. Set
:attr:`~ewoksorange.gui.widgets.hdf5.model.base.Hdf5TreeModel.BACKGROUND_LOADING`
on the model to read them in a worker thread instead, showing a loading item
rather than blocking. It is off by default because a worker thread reading a
file races with this process writing that same file. With it on, a file is not
in the tree yet when ``updateFile`` returns;
:meth:`~ewoksorange.gui.widgets.hdf5.viewer.Hdf5Viewer.waitForLoading` waits
for it.

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

A :term:`tree model` opens every file through
:meth:`~ewoksorange.gui.widgets.hdf5.model.base.Hdf5TreeModel.openFile`, which
returns any h5py-like object, so a regime the models above do not cover is a
matter of overriding it:

.. code-block:: python

    from ewoksorange.gui.widgets.hdf5.model.base import Hdf5TreeModel

    class MyTreeModel(Hdf5TreeModel):
        DEFAULT_OPEN_OPTIONS = {"mode": "r"}

        def openFile(self, filename):
            return MyFileProxy(filename, **self._open_options)

:attr:`~ewoksorange.gui.widgets.hdf5.model.base.Hdf5TreeModel.DEFAULT_OPEN_OPTIONS`
completes the options given at instantiation. Override
:meth:`~ewoksorange.gui.widgets.hdf5.model.base.Hdf5TreeModel.exists` as well
when a file name does not refer to a path on disk:

.. code-block:: python

    from silx.io import commonh5

    class MemoryTreeModel(Hdf5TreeModel):
        def exists(self, filename):
            return filename in self.contents

        def openFile(self, filename):
            h5file = commonh5.File(filename, mode="r")
            h5file.add_node(commonh5.Dataset("data", self.contents[filename]))
            return h5file

The proxies the models return live in :mod:`ewoksorange.io.hdf5` and need no
GUI. Reuse one by pointing ``FILE_CLASS`` at a subclass, for instance to change
how a reopening proxy opens its file:

.. code-block:: python

    from ewoksorange.gui.widgets.hdf5.model.live import LiveFileTreeModel
    from ewoksorange.io.hdf5.live import LiveFile

    class MyFile(LiveFile):
        def open_h5_file(self, filename, **open_options):
            return MyH5pyFileContextManager(filename, **open_options)

    class MyTreeModel(LiveFileTreeModel):
        FILE_CLASS = MyFile

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
