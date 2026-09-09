.. _hdf5_access:

HDF5 access
===========

An Orange canvas running Ewoks tasks opens the same HDF5 files from two places
in one process:

- an :term:`Ewoks task`, which lives only as long as it executes, and reads
  its input file or writes its output file;
- an :class:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget`, which lives as
  long as the :term:`Orange canvas` does, and reads either of those files to
  show them.

Which mode each of them may use is not a free choice. HDF5 does not pick a
mode: it opens what it is asked for, but it refuses combinations which cannot
hold at the same time, and those constraints are about the file rather than
about the opener. This page explains which combinations are refused, what
follows from that, and where the sharp edges are.

Which combinations are refused
------------------------------

Opening a file which this process already has open. An open which succeeds
returns the mode in the cell, which is not always the mode asked for. Whether
a lock is taken is the :term:`file locking` flag:

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

Opening a file which **another process** has open for writing:

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

Two things follow, and everything else on this page is a consequence of them:

#. Only the diagonal of the first table works. A second opener in the same
   process cannot pick its own mode: it joins the mode already in use, or the
   open is refused.
#. A file another process is writing can only be read read-only **and
   unlocked**. Taking the lock, or asking for write access, fails.

One regime per file
-------------------

Because the mode belongs to the file rather than to the opener, a file falls in
one of three :term:`access regimes <Access regime>`, and every opener in the
process conforms to it:

.. mermaid::

    flowchart TD
        A[A file to open] --> B{May another process<br/>write it?}
        B -- yes --> E["<b>Externally written</b><br/>open 'r' unlocked"]
        B -- no --> C{Does a task in this<br/>process write it?}
        C -- yes --> O["<b>Ours</b><br/>open 'a'"]
        C -- no --> S["<b>Static</b><br/>open 'r'"]

.. list-table::
    :header-rows: 1
    :widths: 18 30 12 40

    * - Regime
      - When
      - Mode
      - What it implies
    * - Externally written
      - another process may write it, now or later
      - ``r`` unlocked
      - unlocked is what leaves the writer unblocked; no task in this process
        can write it, and reads need a :term:`reading policy` because opening
        a file being written can fail
    * - Ours
      - a task in this process writes it
      - ``a``
      - no other process can write it; every reader in this process, the
        widget included, joins at ``a``
    * - Static
      - nobody writes it
      - ``r``
      - nothing to tolerate

This is why there is no matrix of task modes against widget modes to fill in:
classify the file, and both openers follow.

What a reader can see
---------------------

Two things limit what a reader of an :term:`externally written file` sees, and
neither is about which mode it opened with:

* A handle which is kept open never sees anything written after it was opened.
  Reopening the file is what makes a later read show more, which is why the
  models for this regime close the file between reads.
* Without :term:`SWMR`, a writer only makes its writes visible to other
  processes when it closes the file. A reader therefore shows the state the
  writer last left behind, not what it is writing now, however often it
  reopens.

So a viewer refreshed while an acquisition runs advances when the writer closes
the file, for instance between scans, rather than continuously. A writer using
:term:`SWMR` is the case where a reader can follow along, by refreshing its own
handle.

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

**A widget cannot hold a file open.** A persistent read-only handle makes a
later ``a`` in the same process fail with *already open for read-only*, so a
widget which keeps a file open stops a task from ever writing it. Widgets
therefore open, read and close, which is what
:class:`~ewoksorange.io.hdf5.live.LiveFile` does.

**Opening and closing is not enough on its own.** A read which merely overlaps
a task opening the file for writing still fails. Either the writer retries, or
the reader is not triggered while the task runs.

**A file this process writes is not open to external writers.** The two cannot
be arranged at once: while a task holds ``a``, another process cannot take the
lock, and while another process writes, ``a`` cannot be taken. A file is in one
regime at a time, even if it is the output of one task and the input of the
next.

**Read-only is not enforceable in this process.** Asking for ``a`` yields
``r+``, and ``h5py`` hands a writable handle to a caller asking for ``r``
when the file is already open for writing. Nothing prevents a widget from
modifying a file through a handle it was given; only the code in the widget
does.

**External links are separate files with their own regime.** An
:term:`external link` from a file this process writes may point at raw data
another process is writing. The master is
opened ``a`` and the link target ``r`` unlocked, which is allowed because the
two are different files. ``h5py`` opens a link target with the options of
the file holding the link, which is the wrong regime for the target, so the
target is opened separately by
:class:`~ewoksorange.io.hdf5.links.LinkAwareFile`.

**A virtual dataset reaches other files without a link.** The sources of a
:term:`virtual dataset` are separate files with their own regime, just like an
:term:`external link` target, but there is no link to intercept: ``h5py`` opens
them when the dataset is read, with the mode of the file holding it. Reading
such a dataset from a file opened ``a`` therefore opens raw data this process
does not write in ``a`` as well, which fails when it cannot be written. HDF5
does not report that failure: the read returns the fill value of the dataset,
so wrong data rather than an error, unless the libhdf5 in use raises instead.
:class:`~ewoksorange.io.hdf5.links.LinkAwareFile` re-creates the dataset in a
temporary file it opens itself, mapping onto the same sources, so they are
opened in their own regime. No data is copied.

**A virtual dataset locks its sources.** HDF5 takes the :term:`file locking`
flag on the source files while the file holding the dataset is open, whichever
flag that file was opened with. A source read unlocked elsewhere in the process
afterwards is therefore refused, which is what the second attempt of
:func:`~ewoksorange.io.hdf5.access.open_for_reading` joins.

**SWMR is the alternative to unlocked reads.** Reading unlocked and retrying is
what is left when the writer does not use :term:`SWMR`. When it does, readers can rely on it instead of retrying.

See :ref:`How to browse HDF5 data ?` for the classes implementing this.
