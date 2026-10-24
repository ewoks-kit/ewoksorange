Glossary
========

.. glossary::
    :sorted:

    Ewoks task
        An `ewoks <https://ewoks.readthedocs.io/>`_ task: a class deriving from
        ``ewokscore.Task`` that declares its inputs and outputs and implements ``run()``.
        Each execution creates a new instance of the task class, which lives only as long
        as it executes.

    Widget
        An Orange widget that executes an :term:`Ewoks task`, deriving from
        :class:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget`. It submits its task to
        its :term:`executor` when it is triggered (by default when its inputs change), then
        propagates the outputs downstream when the task succeeds, or invalidates them when
        it fails.

    Execution
        One run of an :term:`Ewoks task`, from its submission to the :term:`executor` to
        the ``finished`` signal. Each submission is a new execution, with its own
        :term:`task future`.

    Queued execution
        An :term:`execution` that was submitted but did not start yet: it waits for a free
        :term:`worker` (and, in the ``"process"`` :term:`backend`, for the
        controller's permission to start).

    Submit policy
        What the :term:`executor` does with a submission while an :term:`execution` is
        running, selected by the ``submit_policy`` class argument of a :term:`widget`:
        ``"always"`` (the default) queues it, ``"drop_if_busy"`` drops it.

    Executor
        The :class:`~ewoksorange.gui.concurrency.executor.EwoksExecutor` that executes the
        :term:`Ewoks tasks <Ewoks task>` of a :term:`widget` with a :term:`backend` and
        emits Qt signals for each step of an :term:`execution`. Each signal carries the
        :term:`task future` of the execution, except ``ignored``.

    Backend
        Where the :term:`executor` executes an :term:`Ewoks task`, selected by the
        ``concurrency`` class argument of a :term:`widget`
        (:class:`~ewoksorange.gui.concurrency.executor.Concurrency`): ``"sync"`` in the
        :term:`GUI thread`, ``"thread"`` (the default) in a thread pool or ``"process"`` in
        a process pool.

    Worker
        A thread of the thread pool or a process of the process pool that executes
        :term:`Ewoks tasks <Ewoks task>`, one at a time.

    Task future
        The :class:`~ewoksorange.gui.concurrency.future.TaskFuture` returned by
        :meth:`~ewoksorange.gui.concurrency.executor.EwoksExecutor.submit_task`. It gives
        the outputs or the error of the execution, and can :term:`cancel`,
        :term:`stop <stop request>`, :term:`abort` or :term:`kill` it.

    Progress object
        The optional ``progress`` task argument, usually a
        :class:`~ewoksorange.gui.qt_utils.progress.QProgress`. A task deriving from
        ``ewokscore.TaskWithProgress`` reports its progress, as a percentage, by assigning
        ``self.progress``. A ``QProgress`` emits ``sigProgressChanged`` when the percentage
        changes, in the thread that assigns it.

    GUI thread
        The main thread of the Qt application, in which the :term:`widgets <widget>` and the
        :term:`executor` live.

    Queued connection
        How Qt delivers a signal emitted in a thread other than the thread of the receiver:
        the signal is posted to the event queue of the receiver's thread, and the connected
        slots run later, when that thread processes its events. Signals posted to the same
        thread are processed in the order they were posted. Qt uses it by default for
        signals emitted in another thread.

    Cancel
        Prevent a queued :term:`Ewoks task` from starting
        (:meth:`TaskFuture.cancel() <ewoksorange.gui.concurrency.future.TaskFuture.cancel>`).
        It has no effect on a running task.

    Stop request
        Ask an :term:`Ewoks task` to stop
        (:meth:`TaskFuture.request_stop() <ewoksorange.gui.concurrency.future.TaskFuture.request_stop>`).
        It is cooperative: a running task decides whether and how to stop, by checking
        ``Task.stop_requested`` or implementing ``Task._on_stop_requested``.

    Abort
        Interrupt an :term:`Ewoks task` running in a :term:`worker` process like Ctrl-C
        (:meth:`TaskFuture.abort() <ewoksorange.gui.concurrency.future.TaskFuture.abort>`),
        also when it ignores :term:`stop requests <stop request>`. The task can clean up and
        the :term:`worker` survives.

    Kill
        Terminate the :term:`worker` process running an :term:`Ewoks task`
        (:meth:`TaskFuture.kill() <ewoksorange.gui.concurrency.future.TaskFuture.kill>`). It
        also works when the task does not return to the Python interpreter, but the task
        cannot clean up. The pool replaces the :term:`worker`.

    pebble
        The `third-party process pool <https://github.com/noxdafox/pebble>`_ of the
        ``"process"`` :term:`backend`. Unlike ``concurrent.futures.ProcessPoolExecutor``, it
        can :term:`kill` one task without breaking the pool.

    Manager
        The ``multiprocessing`` manager: a separate server process holding the queues
        through which the :term:`GUI thread`'s process and the :term:`worker` process
        communicate in the ``"process"`` :term:`backend`. Each :term:`executor` starts one
        manager process on its first :term:`execution` and stops it on shutdown. All its
        executions share it.

    Relay
        A thread of the :term:`GUI thread`'s process that reads the messages of a
        :term:`worker` process from the :term:`manager` queue and turns them into Qt signals.
        It also replies whether the task may start. One relay thread runs per execution in
        the ``"process"`` :term:`backend`.

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
        A file a task in this process may write, now or later, normally the
        output of that task. No other process can write it, and every reader in
        this process, a widget included, reads it read-write, which is the only
        mode a task can join whenever it opens the file.

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
        Single Writer Multiple Reader, the HDF5 mode in which a reader keeps its
        handle open and refreshes it to see what the writer adds. Without it a
        writer still makes its writes visible by flushing the file, but a reader
        has to reopen the file to see them.

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
        The :class:`~ewoksorange.gui.widgets.hdf5.model.Hdf5TreeModel` given to
        a viewer. It decides which files can be browsed and opens each of them
        with its :term:`access class`.

    Access class
        The class a :term:`tree model` opens its files with, for instance
        :class:`~ewoksorange.io.hdf5.live.LiveFile`. It takes a file name and
        returns a read-only :mod:`silx.io.commonh5` view of it, so choosing an
        access class is how an :term:`access regime` and a :term:`reading
        policy` are applied.

    Orange canvas
        The desktop application of `Orange <https://orangedatamining.com/>`_
        in which Ewoks workflows are edited and executed. A widget on the
        canvas lives as long as the workflow does, which is why a widget must
        not hold a file open.

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
