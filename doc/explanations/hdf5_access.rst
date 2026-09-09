.. _hdf5_access:

HDF5 access
===========

An Orange canvas running Ewoks tasks opens the same HDF5 files from two places
in one process: an :term:`Ewoks task`, which lives only as long as it executes
and reads its input or writes its output, and a widget, which lives as long as
the :term:`Orange canvas` does and shows either of those files.

Which mode each of them may use is not a free choice: HDF5 refuses
combinations which cannot hold at the same time, and those constraints are
about the file, not about the opener.

In short
--------

Classify the file by who may write it. That :term:`access regime` decides the
mode, and the mode decides the class, for the task and the widget alike:

.. mermaid::

    flowchart TD
        A[A file to open] --> B{May another process<br/>write it?}
        B -- yes --> E["<b>Externally written</b><br/>open 'r' unlocked"]
        B -- no --> C{Does a task in this<br/>process write it?}
        C -- yes --> O["<b>Owned</b><br/>open 'r+'"]
        C -- no --> S["<b>Static</b><br/>open 'r'"]

.. list-table::
    :header-rows: 1
    :widths: 22 30 12 36

    * - Regime
      - When
      - Mode
      - Class to read it with
    * - :term:`Externally written <Externally written file>`
      - another process may write it, now or later
      - ``r`` unlocked
      - :class:`~ewoksorange.io.hdf5.live.LiveFile`
    * - :term:`Owned <Owned file>`
      - a task in this process may write it, now or later
      - ``r+``
      - :class:`~ewoksorange.io.hdf5.owned.OwnedFile`
    * - :term:`Static <Static file>`
      - nobody writes it
      - ``r``
      - :class:`~ewoksorange.io.hdf5.static.StaticFile`

Three rules follow, and the rest of this page is why they hold:

#. **One regime per file.** A second opener in the same process cannot pick
   its own mode: it joins the mode already in use, or its open is refused.
   Which of them opens the file first is a race, so the mode has to be the one
   that holds in every order.
#. **Read unlocked whenever possible.** A lock taken here blocks a writer in
   another process, and refuses it the file when it starts writing later.
#. **A widget gives way to everything.** It holds no file open, it cannot
   write, and it reports a file it cannot read through
   :attr:`~ewoksorange.gui.widgets.hdf5.tree_viewer.Hdf5TreeViewer.sigFileFailed`
   instead of raising.

:ref:`How to browse HDF5 data ?` puts these classes in a widget.

Who gives way to whom
---------------------

Three things open these files, and they do not have equal claim on them:

#. **A writer in another process**, such as an acquisition. It must never be
   affected by anything done here: not blocked, not slowed, not refused the
   file when it opens it later, and never written to.
#. **An** :term:`Ewoks task`. Processing the data is what the canvas is run
   for, so a task yields to an external writer but to nothing else: a widget
   must never make a task fail to read its input or write its output.
#. **A widget**, which only shows data. It gives way to both, absorbs its own
   failures rather than raising, and reports them so that what is on screen can
   be trusted or distrusted knowingly.

That order is where the three rules come from. Reading unlocked comes first
because it is what leaves an external writer alone, whether it is writing
already or starts while the file is being read. A widget holds no file open
because a held handle stops a task from writing that file. A widget reports
instead of raising because a failed read must not stop the canvas, and a
silently missing file is worse than a reported one.

Which combinations are refused
------------------------------

HDF5 does not pick a mode: it opens what it is asked for, but refuses what
cannot hold at the same time. These two tables are the whole of it.

.. dropdown:: Opening a file this process already has open

    An open which succeeds returns the mode in the cell, which is not always
    the mode asked for. Whether a lock is taken is the :term:`file locking`
    flag:

    .. list-table::
        :header-rows: 1
        :widths: 22 26 26 26

        * - already held
          - request ``r`` unlocked
          - request ``r`` locked
          - request ``a``
        * - nothing
          - opens as ``r``
          - opens as ``r``
          - opens as ``r+``
        * - ``r`` unlocked
          - opens as ``r``
          - refused: locking flags do not match
          - refused: already open read-only
        * - ``r`` locked
          - refused: locking flags do not match
          - opens as ``r``
          - refused: already open read-only
        * - ``a``
          - refused: locking flags do not match
          - refused: locking flags do not match
          - opens as ``r+``

    Only the diagonal works, which is rule 1: a second opener joins the mode
    already in use, or it is refused.

.. dropdown:: Opening a file another process has open for writing

    .. list-table::
        :header-rows: 1
        :widths: 30 70

        * - request
          - outcome
        * - ``r`` unlocked
          - opens as ``r``
        * - ``r`` locked
          - refused: unable to lock the file
        * - ``a``
          - refused: unable to lock the file

    Such a file can only be read read-only **and** unlocked, which is rule 2.
    Taking the lock, or asking for write access, fails.

What each regime implies:

* **Externally written**: no task in this process can write the file, and
  reads need a :term:`reading policy` because opening a file being written can
  fail.
* **Owned**: no other process can write the file, and every reader in this
  process, the widget included, reads it read-write. Not because it writes
  anything, but because a task can open the file before, during or after such a
  read, and ``r+`` is the only mode which works in each of those orders: a
  handle held read-only refuses the task, and one held read-write is joined by
  it. Read-write is also what a task already holding the file is joined at.
* **Static**: nothing to tolerate.

So there is no matrix of task modes against widget modes to fill in: classify
the file, and both openers follow. Each regime is an :term:`access class` of
:mod:`ewoksorange.io.hdf5`, all of them reading through the same
:mod:`silx.io.commonh5` view.

What a reader can see
---------------------

What a reader of an :term:`externally written file` sees is not decided by the
mode it opened with:

* A writer makes its writes visible by flushing the file, or by closing it,
  which flushes. A reader sees everything flushed before it opened the file.
* A handle which is kept open never sees writes which land after it was
  opened. Reopening the file is what makes a later read show more, which is
  why :class:`~ewoksorange.io.hdf5.live.LiveFile` closes the file between
  reads.
* The structure changes as well, not only the content. A part of the file
  which has not been read yet is read when it is first looked at, so expanding
  a group shows what the writer has added to it since. A part which has been
  read stays as it was read until the file is opened again.
* Everything else is read from the file on every access: the content of a
  dataset, its extent, which grows while a writer appends to it, and the
  attributes of groups and datasets alike. Only the children of a group are a
  snapshot, so only a group which was already expanded needs a refresh.

A viewer refreshed while an acquisition runs therefore does follow the
acquisition, as long as the writer flushes, which is the normal case. What it
cannot do is see a write which has not been flushed yet, and a read which
lands midway through a flush fails, which is what a :term:`reading policy`
with a retry is for.

:term:`SWMR` differs in that the reader may keep its handle open and refresh it
instead of reopening the file.

Reading a file which is being written
-------------------------------------

Only the :term:`externally written <Externally written file>` regime needs a
:term:`reading policy`, and the choice is between how faithful the read is and
how much it may cost or fail:

.. list-table::
    :header-rows: 1
    :widths: 34 66

    * - Policy
      - Use for
    * - best effort, absorb failures
      - showing whatever is readable now, like a viewer
    * - best effort, fail otherwise
      - a task which can report that its input was not readable
    * - faithful, retry until readable
      - a task which must read what the writer wrote, using the retrying
        helpers of :mod:`silx.io.h5py_utils` or ``blissdata``
    * - faithful, assume static, fail otherwise
      - a task reading a finished acquisition, where a failure means the
        assumption was wrong
    * - faithful, assume static, absorb failures
      - the same, where a missing input is not an error

A widget always absorbs failures: a read which raises must not crash the
canvas or raise a dialog per refresh. It should, however, stay able to show
that what is on screen is older than the file, because a silently absorbed
failure and "nothing changed" look the same to the user otherwise.

Sharp edges
-----------

.. dropdown:: A widget cannot hold a file open read-only

    A persistent read-only handle makes a later ``a`` in the same process fail
    with *already open for read-only*, so a widget which keeps a file open
    read-only stops a task from ever writing it. That is why
    :class:`~ewoksorange.io.hdf5.owned.OwnedFile` reads read-write and why
    :class:`~ewoksorange.io.hdf5.live.LiveFile`, which cannot read-write a file
    another process is writing, opens and closes around every read instead.

.. dropdown:: Opening and closing is not enough on its own

    Opening a file read-only for the duration of a read, however short, still
    refuses a task which asks for write access in that window. Only reading it
    read-write removes that window, which is possible for an
    :term:`owned file <Owned file>` and never for an :term:`externally written
    file`: there, either the writer retries, or the reader is not triggered
    while the task runs.

.. dropdown:: A file this process writes is not open to external writers

    The two cannot be arranged at once: while a task holds ``a``, another
    process cannot take the lock, and while another process writes, ``a``
    cannot be taken. A file is in one regime at a time, even if it is the
    output of one task and the input of the next.

.. dropdown:: Read-only is not enforceable through the mode

    Asking for ``a`` yields ``r+``, and ``h5py`` hands a writable handle to a
    caller asking for ``r`` when the file is already open for writing. What
    makes a widget harmless is therefore not the mode it opened with but the
    view it reads through: :class:`~ewoksorange.io.hdf5.base.Hdf5File` exposes
    the :mod:`silx.io.commonh5` API, which cannot write.

.. dropdown:: External links are separate files with their own regime

    An :term:`external link` from a file this process writes may point at raw
    data another process is writing. The master is opened ``a`` and the link
    target ``r`` unlocked, which is allowed because the two are different
    files. ``h5py`` opens a link target with the options of the file holding
    the link, which is the wrong regime for the target, so the target is
    opened separately by
    :meth:`~ewoksorange.io.hdf5.base.Hdf5File.open_external_h5_file`.

.. dropdown:: A virtual dataset reaches other files without a link

    The sources of a :term:`virtual dataset` are separate files with their own
    regime, just like an :term:`external link` target, but there is no link to
    intercept: ``h5py`` opens them when the dataset is read, with the mode of
    the file holding it. Reading such a dataset from a file opened ``a``
    therefore opens raw data this process does not write in ``a`` as well,
    which fails when it cannot be written. HDF5 does not report that failure:
    the read returns the fill value of the dataset, so wrong data rather than
    an error, unless the libhdf5 in use raises instead.
    :class:`~ewoksorange.io.hdf5.base.Hdf5File` re-creates the dataset in a
    temporary file it opens itself, mapping onto the same sources, so they are
    opened in their own regime. No data is copied.

.. dropdown:: A virtual dataset locks its sources

    HDF5 takes the :term:`file locking` flag on the source files while the file
    holding the dataset is open, whichever flag that file was opened with. A
    source read unlocked elsewhere in the process afterwards is therefore
    refused, which is what the second attempt of
    :func:`~ewoksorange.io.hdf5.access.open_for_reading` joins.

    Before libhdf5 1.14.4 the flag of that file is not passed on and the
    sources are opened with the default flag, which is locked. A source this
    process already has open unlocked is then not reached at all, and the read
    returns the fill value of the dataset.

.. dropdown:: SWMR is the alternative to unlocked reads

    Reading unlocked and retrying is what is left when the writer does not use
    :term:`SWMR`. When it does, readers can rely on it instead of retrying.

See :ref:`How to browse HDF5 data ?` for the classes implementing this.
