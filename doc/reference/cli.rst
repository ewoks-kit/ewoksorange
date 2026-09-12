.. _cli:

CLI reference
=============

python -m ewoksorange.gui.widgets.hdf5
--------------------------------------

.. argparse::
    :module: ewoksorange.gui.widgets.hdf5.__main__
    :func: create_argument_parser
    :prog: python -m ewoksorange.gui.widgets.hdf5

    Browse the ``files`` given on the command line with
    :class:`~ewoksorange.gui.widgets.hdf5.viewer.Hdf5Viewer`, the widget the
    Orange widgets use, so what is shown here is what they show.

    Files can be opened while another process writes them, and while this
    process writes them. ``--access`` selects the :term:`tree model`, one value
    per :term:`access regime`; see :ref:`How to browse HDF5 data ?` for what
    each of them does and for building another combination.

    .. code-block:: bash

        python3 -m ewoksorange.gui.widgets.hdf5 --access owned results.h5

    Use ``--tree-only`` to leave out the data panel, which gives
    :class:`~ewoksorange.gui.widgets.hdf5.tree_viewer.Hdf5TreeViewer` on its
    own.

    .. tip::

        ``--demo`` needs no data of its own: it generates a file holding one
        NXdata plot type per NXentry (a curve, an image, a stack and a
        scatter), and adds a group action and a dataset action to the context
        menu of the tree, so both can be tried out immediately.

        .. code-block:: bash

            python3 -m ewoksorange.gui.widgets.hdf5 --demo
