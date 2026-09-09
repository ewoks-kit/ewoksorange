Glossary
========

.. glossary::
    :sorted:

    Access regime
        The access regime of an HDF5 file says who may write it, and therefore how
        every opener in this process must open it. A file is :term:`static <Static
        file>`, :term:`externally written <Externally written file>` or
        :term:`owned <Owned file>`. HDF5 refuses combinations of modes which cannot
        hold at the same time, so the regime belongs to the file rather than to the
        code opening it. See :ref:`hdf5_access`.

    Static file
        A file no process writes. It can be read read-only and needs no
        :term:`reading policy`.

    Externally written file
        A file another process may write, such as raw data a running
        :term:`BLISS` acquisition is writing. It can only be read read-only and
        without :term:`file locking`, no task in this process can write it, and
        reads need a :term:`reading policy` because they can see a half-written
        file.

    Owned file
        A file a task in this process writes, normally the output of that task. It
        is opened in append mode, no other process can write it, and every reader
        in this process, a widget included, joins that same mode.

    Reading policy
        What a reader does when reading an :term:`externally written file`
        fails: read on a best-effort basis and absorb the failure, read on a
        best-effort basis and raise, or retry until the data is readable. A
        widget always absorbs failures, a :term:`Ewoks task` chooses.

    File locking
        The HDF5 mechanism which stops a file being written and read
        inconsistently at the same time. Two handles on one file in the same
        process must agree on their locking flags, and a locked reader blocks a
        writer in another process, which is why an :term:`externally written
        file` is read unlocked.

    SWMR
        Single Writer Multiple Reader, the HDF5 mode in which a writer publishes
        its writes to readers while it keeps the file open, and a reader
        refreshes its handle to see them. Without it a writer only makes its
        writes visible by closing the file, so a reader sees the state it last
        left behind.

    External link
        A link from one HDF5 file into another. :term:`h5py` opens the target
        with the options of the file holding the link, which is the wrong
        :term:`access regime` whenever the two files differ, so *ewoksorange*
        opens the target itself.

    Virtual dataset
        A dataset whose data lives in other datasets, possibly in other files.
        :term:`h5py` opens those sources when the dataset is read, with the
        options of the file holding it, which is the wrong :term:`access
        regime` whenever the sources are in another file. There is no link to
        intercept, so *ewoksorange* re-creates the dataset in a temporary file it
        opens itself: the same mapping onto the same sources, no data copied.

    Tree model
        The :class:`~ewoksorange.gui.widgets.hdf5.model.base.Hdf5TreeModel`
        given to a viewer. It decides which files can be browsed and how they
        are opened, so choosing a tree model is how an :term:`access regime` and
        a :term:`reading policy` are applied.

    Ewoks task
        The unit of work an Orange widget executes. It lives only as long as it
        executes, and reads its input file or writes its output file.

    Orange canvas
        The desktop application in which Ewoks workflows are edited and
        executed. A widget on the canvas lives as long as the workflow does,
        which is why a widget must not hold a file open.

    BLISS
        `BLISS <https://bliss.gitlab-pages.esrf.fr/bliss>`_ is the ESRF
        experiment control system. It writes HDF5 files while they are being
        read, which is the reason :term:`externally written files <Externally
        written file>` exist.

    silx
        `silx <https://silx.readthedocs.io/>`_ provides the HDF5 tree and data
        widgets *ewoksorange* builds on, and the HDF5 helpers in
        :mod:`silx.io.h5py_utils`.

    h5py
        `h5py <https://docs.h5py.org/>`_ is the Python interface to HDF5.

    NeXus
        `NeXus <https://www.nexusformat.org/>`_ is the convention for the
        contents of an HDF5 file used at synchrotrons. An ``NXdata`` group in it
        says which arrays to plot and how.
