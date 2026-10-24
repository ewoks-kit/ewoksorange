Execution Backends
==================

A :term:`widget` executes its :term:`Ewoks task` through an :term:`executor`, in one of
three :term:`backends <backend>`: in the :term:`GUI thread`, in a thread pool or in a
process pool. This page has two parts:

- :ref:`concurrency-contract`, for widget authors: which backend to choose, how to end an
  :term:`execution`, and which signals arrive in which order.
- :ref:`concurrency-implementation`, for maintainers: how each backend keeps that order.

See :doc:`execution` for how an execution fits in the life of a workflow.

.. _concurrency-contract:

Contract
--------

Executing from a widget
^^^^^^^^^^^^^^^^^^^^^^^

A widget executes its task with
:meth:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.execute_ewoks_task`, which
returns the :term:`task future` of the execution, or ``None`` when the submission was
dropped. The executor of the widget is
:attr:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.task_executor`.

:class:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget` already handles the signals of
its executor: it starts the progress bar on ``aboutToStart``, and on ``succeeded`` or
``failed`` it propagates the outputs downstream or invalidates them, then stops the
progress bar. Connect to the signals only to do more than that.

A widget configures its executor with class arguments:

- ``concurrency``: the :term:`backend`, see below.
- ``max_workers``: how many executions can run at the same time (``None`` for the pool
  default). Ignored by the ``"sync"`` backend.
- ``submit_policy``: what to do with a submission while an execution is running:

  - ``"always"`` (the default): queue it until a :term:`worker` is free.
  - ``"drop_if_busy"``: drop it.

- ``mp_context``: the start method of the worker processes (``"spawn"`` by default). Only
  used by the ``"process"`` backend.

Choosing a backend
^^^^^^^^^^^^^^^^^^

.. list-table::
    :header-rows: 1

    * - ``concurrency``
      - The task runs in
      - The GUI stays responsive
      - Ways to end an execution
      - Requirements
    * - ``"sync"``
      - the :term:`GUI thread`, inside ``submit_task()``
      - no, not even to display progress
      - :term:`cancel` and :term:`stop request`, only from a slot connected to the
        signals of the execution
      -
    * - ``"thread"`` (default)
      - a :term:`worker` thread
      - yes
      - :term:`cancel`, :term:`stop request`
      -
    * - ``"process"``
      - a :term:`worker` process
      - yes
      - :term:`cancel`, :term:`stop request`, :term:`abort`, :term:`kill`
      - the task class must be importable and its inputs and outputs picklable

Ending an execution
^^^^^^^^^^^^^^^^^^^

The :term:`task future` can end an execution, from mild to forceful:

.. list-table::
    :header-rows: 1

    * - Method
      - On a :term:`queued <queued execution>` task
      - On a running task
      - Then ``result()``
    * - ``cancel()``
      - the task never starts
      - no effect
      - raises ``CancelledError``
    * - ``request_stop()``
      - the task never starts
      - the task decides whether and how to stop
      - raises :class:`~ewoksorange.gui.concurrency.future.TaskStoppedError` when the task
        never started, otherwise returns or raises what the task does
    * - ``abort()``
      - the task never starts
      - interrupted like Ctrl-C (the task sees a ``KeyboardInterrupt``) once it runs
        Python code again, so it can clean up
      - raises :class:`~ewoksorange.gui.concurrency.future.TaskAbortedError` when the task
        was interrupted
    * - ``kill()``
      - the task never starts
      - its process is terminated, it cannot clean up
      - raises :class:`~ewoksorange.gui.concurrency.future.TaskKilledError`

``CancelledError`` is ``concurrent.futures.CancelledError``.

Each method returns ``True`` when it prevented the start or reached the running task. On
a queued task, the first call decides: the task never starts, and later calls return
``False``. On a running task, ``request_stop()`` and ``abort()`` can be repeated, and the
calls can escalate, for example ``request_stop()``, then ``abort()``, then ``kill()``.
None of them has an effect on a finished task, which includes a task ended by ``kill()``.
``abort()`` and ``kill()`` have no effect in the ``"sync"`` and ``"thread"`` backends.

A task honours ``request_stop()`` by checking ``self.stop_requested`` or by implementing
``_on_stop_requested()`` (see `ewokscore <https://ewokscore.readthedocs.io/>`_).

How a running task reacts to a stop request is up to the task: it can raise, return early
with missing or partial outputs, or complete normally. After a stop request,
``succeeded`` therefore does not mean that the outputs are complete: check
``stop_requested()`` before using them.

Signals
^^^^^^^

The :term:`executor` emits these signals, each carrying the :term:`task future` except
``ignored``:

- ``submitted``: the task was submitted.
- ``aboutToStart``: the task is about to be created.
- ``started``: the task was created and is about to execute.
- ``cancelled``: ``cancel()`` prevented the start.
- ``stopRequested``: ``request_stop()`` prevented the start or reached the running task.
- ``aborted`` / ``killed``: ``abort()`` / ``kill()`` prevented the start or ended the task.
- ``succeeded`` / ``failed``: the task finished without / with an exception.
- ``finished``: the execution is over.
- ``ignored`` (no argument): a submission was dropped by ``submit_policy="drop_if_busy"``.

Progress values are not executor signals: the :term:`progress object` emits
``sigProgressChanged`` when the progress reported by the task changes. They keep their
order with respect to the executor signals in all backends.

These signals arrive in the following order, after ``submitted``:

.. list-table::
    :header-rows: 1

    * - Case
      - Signals after ``submitted``
    * - The task succeeds
      - ``aboutToStart``, ``started``, progress values, ``succeeded``, ``finished``
    * - The task raises
      - ``aboutToStart``, ``started`` (not when creating the task raises), progress
        values, ``failed``, ``finished``
    * - Cancelled before it starts
      - ``cancelled``, ``finished``
    * - Stop requested before it starts
      - ``stopRequested``, ``failed``, ``finished``
    * - Aborted before it starts
      - ``aborted``, ``failed``, ``finished``
    * - Killed before it starts
      - ``killed``, ``failed``, ``finished``
    * - Stop requested while running
      - ``aboutToStart``, ``started``, progress values, ``stopRequested``, then
        ``failed`` when the task raises, otherwise ``succeeded`` (with complete, partial
        or missing outputs), ``finished``
    * - Aborted while running
      - ``aboutToStart``, ``started``, progress values, ``aborted``, ``failed``,
        ``finished``
    * - Killed while running
      - ``aboutToStart``, ``started``, progress values, ``killed``, ``failed``,
        ``finished``
    * - The worker process crashes (``"process"`` only)
      - ``aboutToStart``, ``started``, progress values, ``failed``, ``finished``

The signals arrive only as far as the execution got: a stop request, an abort or a kill
can arrive before ``aboutToStart`` or ``started`` were emitted. An abort that does not
interrupt the task in time (the task ends first, or it catches ``KeyboardInterrupt``)
gives the signals of a task that was not aborted. A submission dropped by
``submit_policy="drop_if_busy"`` only emits ``ignored``.

What this means for a widget:

- ``finished`` is the last signal of every submitted execution, so it is the place to
  release what the execution uses.
- No ``aboutToStart``, ``started`` or progress value arrives after the other signals of the
  execution, unless the relay of the ``"process"`` backend times out (see below).
- An execution can finish without ever emitting ``aboutToStart`` or ``started``.
- ``failed`` is also emitted for an execution that was stopped, aborted or killed. The
  task future tells why with ``stop_requested()``, ``aborted()`` and ``killed()``, and
  ``cancelled()`` for a cancelled execution.
- Connect to the signals with the default connection type (plain ``connect()``): all slots
  then run in the GUI thread. Avoid ``Qt.DirectConnection``: such a slot runs in the
  thread that emits the signal, so it must not touch widgets, and it must return quickly
  for the order above to hold (see :ref:`concurrency-implementation`).

.. _concurrency-implementation:

Implementation
--------------

In the diagrams below:

- A solid line with a filled arrowhead is a call or an action.
- A dotted line is a return value, or a message read from a queue.
- A line with an open arrowhead is a Qt signal:

  - ⚡ emitted in the GUI thread: the connected slots run right away.
  - 📨 emitted in another thread: Qt posts it to the event queue of the GUI thread (a
    :term:`queued connection`) and the connected slots run later, when the GUI thread
    processes its events.

- ``_done`` is an internal signal of the executor, not one of the signals above.
- ``progress?`` is the optional ``progress`` task argument. It is kept when the task
  class derives from ``ewokscore.TaskWithProgress``, and dropped otherwise.
- ``[0..n]`` marks a step that is repeated for each progress value, and skipped without a
  :term:`progress object`.

The diagrams show an execution that is not ended early.

In the ``"thread"`` and ``"process"`` backends, the executor does not emit the completion
signals (``cancelled``, ``stopRequested``, ``aborted``, ``killed``, ``succeeded``,
``failed``, ``finished``) from the callback that detects the completion. That callback
can run in any thread, including the GUI thread (in ``kill()``, for example), so it
emits the internal ``_done`` signal, which is always queued to the GUI thread. The
completion signals are then emitted in the GUI thread, after the signals of the
execution that were posted before.

Sync
^^^^

The task runs in the GUI thread, through direct calls. The order is the order of the
calls, and ``submit_task()`` only returns once ``finished`` was emitted.

.. mermaid::

    sequenceDiagram
        box GUI thread
        participant W as Widget
        participant E as EwoksExecutor
        participant R as SyncTaskRunner
        participant T as Task
        end

        W->>E: submit_task(task, progress?)
        E->>E: keep or drop progress
        E-)W: ⚡ submitted
        E->>E: mark the future as running
        E->>R: run
        R-)W: ⚡ aboutToStart
        R->>T: create task
        R-)W: ⚡ started
        R->>T: execute
        T->>T: [0..n] progress = v
        T-)W: [0..n] ⚡ sigProgressChanged(v) of the progress object
        T-->>R: outputs / exception
        R-->>E: outputs / exception
        E->>E: set the future result
        E->>E: add the done callback, which runs right away
        E-)W: ⚡ succeeded / failed
        E-)W: ⚡ finished
        E-->>W: TaskFuture (already done)

Thread
^^^^^^

The task runs in a worker thread, which emits ``aboutToStart``, ``started`` and the
progress values. Qt delivers them in the order they were emitted, since they come from a
single thread.

.. mermaid::

    sequenceDiagram
        box GUI thread
        participant W as Widget
        participant E as EwoksExecutor
        end
        box Worker thread (ThreadPoolExecutor)
        participant R as ThreadTaskRunner
        participant T as Task
        end

        W->>E: submit_task(task, progress?)
        E->>E: keep or drop progress
        E->>R: pool.submit(runner)
        R->>R: wait for ready_event (blocks)
        E-)W: ⚡ submitted
        E->>R: ready_event.set()
        R-)W: 📨 aboutToStart
        R->>T: create task
        R-)W: 📨 started
        R->>T: execute
        T->>T: [0..n] progress = v
        T-)W: [0..n] 📨 sigProgressChanged(v) of the progress object
        T-->>R: outputs / exception
        R->>R: the pool sets the future result, runs the done callback
        R-)E: 📨 _done
        E-)W: ⚡ succeeded / failed
        E-)W: ⚡ finished

``submit_task()`` can only emit ``submitted`` once the pool returned the future, so the
worker waits for ``ready_event`` before it emits anything.

Process
^^^^^^^

The task runs in a worker process, which cannot emit Qt signals in the GUI thread's
process nor update the :term:`progress object` (usually a ``QObject``, which is not
picklable). The ``ProcessTaskController`` in the GUI process and the
``ProcessTaskRunner`` in the worker process communicate through two queues of a
:term:`manager`:

- The queue to the controller carries ``ToController.ABOUT_TO_START``,
  ``ToController.STARTED`` and the progress values: the progress object is replaced by a
  :class:`~ewoksorange.gui.concurrency._messages.QueueProgress`. While the task executes,
  a sender thread of the runner puts each value on this queue, so that an abort never
  interrupts the task thread in the middle of a queue call. The task waits when it
  reports progress faster than the sender thread puts it. The values an aborted task did
  not send yet are dropped. The values reported while the task is created are put
  directly, since an abort cannot interrupt that. The controller puts
  ``ToController.END`` on the queue to end the reading.
- The queue to the runner carries the decision whether the task may start
  (``ToRunner.START`` or a ``StartDenial``), then ``ToRunner.REQUEST_STOP`` and
  ``ToRunner.ABORT``. While the task executes, a thread of the runner reads them, until
  the runner puts ``ToRunner.END`` on it.

The controller has one :term:`relay` thread per execution that reads the queue to the
controller and emits the matching signals. On ``ToController.ABOUT_TO_START``, it decides
whether the task may start (it may not once it was cancelled, stopped, aborted or killed),
replies to the runner, and emits ``aboutToStart`` when allowed. The relay only starts once
``submitted`` was emitted, so the runner cannot start the task before that. The decision
is always the first message to the runner: stop requests and aborts are only put on the
queue to the runner once the start was allowed.

.. mermaid::

    sequenceDiagram
        box GUI thread
        participant W as Widget
        participant E as EwoksExecutor
        end
        box Manager process
        participant M as Queues
        end
        box GUI process: relay thread of the controller
        participant RL as Relay
        end
        box GUI process: pebble pool threads
        participant PP as pebble.ProcessPool
        end
        box Worker process
        participant R as ProcessTaskRunner + Task
        end

        W->>E: submit_task(task, progress?)
        E->>M: create the queue to the controller and the queue to the runner
        E->>E: replace progress by QueueProgress, or drop it
        E->>PP: pool.submit(runner)
        E-)W: ⚡ submitted
        E->>RL: start the relay
        Note over E,RL: only now can the runner start the task
        RL->>M: read the queue to the controller (blocks)
        PP->>R: send the runner to a worker process (pickled)
        R->>M: put ToController.ABOUT_TO_START, then wait for the decision
        M-->>RL: ToController.ABOUT_TO_START
        RL->>M: put ToRunner.START on the queue to the runner
        RL-)W: 📨 aboutToStart
        M-->>R: ToRunner.START
        R->>R: create task
        R->>M: put ToController.STARTED
        M-->>RL: ToController.STARTED
        RL-)W: 📨 started
        R->>R: execute
        R->>M: [0..n] put v
        M-->>RL: [0..n] v
        RL-)W: [0..n] 📨 sigProgressChanged(v) of the progress object
        R-->>PP: outputs / exception (pickled)
        PP->>PP: set the future result, run the done callback
        PP->>M: put ToController.END
        M-->>RL: ToController.END
        RL->>RL: exit
        PP->>RL: join (5 s timeout)
        PP-)E: 📨 _done
        E-)W: ⚡ succeeded / failed
        E-)W: ⚡ finished

The diagram shows the relay reading each message right after it is put; in practice
both run concurrently. What matters is the ordering:

- **One queue, one reader.** All messages to the controller travel through the same
  first-in first-out queue and are handled by its relay thread, so the signals are
  emitted in the order the runner put the messages.
- **All messages before the completion.** The runner puts all its messages, and waits
  for its sender thread to put the progress values, before it returns its result, and
  the done callback only puts ``ToController.END`` once the result is in. A manager queue
  call returns once the message is in the queue, so all messages of the runner are ahead
  of ``ToController.END``. The done callback waits for the relay to reach
  ``ToController.END`` before it emits ``_done``, so the completion signals are emitted
  after all signals of the relay.

The relay's lifetime is tied to the future of the execution, not to a timeout:

- **Prevented from starting.** The runner only puts ``ToController.ABOUT_TO_START``, is
  denied and returns or raises, so the done callback runs and puts ``ToController.END``.
  After ``kill()``, the future of the pool is cancelled instead (see below), so the runner
  may not run at all.
- **Crashed worker.** The pool sets a ``pebble.ProcessExpired`` error on the future and
  replaces the worker process, so the done callback runs and puts ``ToController.END``.
- **Killed worker.** ``kill()`` cancels the future of the pool, which runs the done callback
  right away, in the thread calling ``kill()``, so that thread waits for the relay (at
  most 5 s). The done callback puts ``ToController.END``, so the messages the runner puts after
  that are never read. When a worker already picked up the task, the pool then
  terminates that worker process and replaces it.
- **Manager shut down.** Reading the queue raises and the relay exits.
- **Long-running task.** The relay keeps waiting, since progress may still come. There is
  deliberately no timeout on reading the queue: a timeout would end the relay early and
  silently drop the messages that follow.

The done callback waits at most 5 s for the relay to reach ``ToController.END``. With the
default connections, the relay only posts signals to the GUI thread, so it reaches
``ToController.END`` quickly. A slow slot connected with ``Qt.DirectConnection`` runs in the
relay thread and delays it. When the relay does not reach ``ToController.END`` in time, the
completion signals are emitted anyway, and the remaining signals of the relay follow
them. The same happens when such a slot calls ``kill()``: the done callback then runs in
the relay thread and cannot wait for it.
