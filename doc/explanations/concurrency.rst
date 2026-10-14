Execution Backends
==================

:class:`~ewoksorange.gui.concurrency.executor.EwoksExecutor` runs a task in one
of three ways (see :class:`~ewoksorange.gui.concurrency.executor.Concurrency`):
in the calling thread, in a thread pool or in a process pool. Whatever the
backend, receivers observe the same order of signals for a task:

``submitted`` → ``aboutToStart`` → ``started`` → progress values →
``aborted`` / ``killed`` (if any) → ``succeeded`` / ``failed`` → ``finished``

``stop_requested`` is emitted when the stop is requested, so anywhere after
``submitted``. A task that is stopped, aborted or killed before it starts
skips ``aboutToStart``, ``started`` and progress. A task cancelled before it
starts emits nothing after ``submitted``.

This page explains how each backend preserves that order. In the diagrams below:

- A solid line with a filled arrowhead is a call or an action.
- A dotted line is a return value, or a message read from a queue.
- A line with an open arrowhead is a Qt signal:

  - ⚡ emitted in the GUI thread: the connected slots run right away.
  - 📨 emitted in another thread: Qt posts it to the event queue of the GUI
    thread (a queued connection) and the connected slots run later, when the
    GUI thread processes its events.

- ``progress?`` is the optional ``progress`` task argument: it is only forwarded
  when the task class is a ``TaskWithProgress``, and dropped otherwise.
- ``[0..n]`` marks a step that happens once per progress value the task
  reports, so never without progress.

Sync
----

Everything runs in the calling (GUI) thread, through direct calls. The order
is the order of the calls, and ``submit_task()`` only returns once the task is
done.

.. mermaid::

    sequenceDiagram
        box GUI thread
        participant W as Widget
        participant E as EwoksExecutor
        participant R as SyncTaskRunner
        participant T as Task
        end

        W->>E: submit_task(task, progress?)
        E->>E: _handle_progess_arg: keep or drop progress
        E-)W: ⚡ submitted
        E->>R: _sync_submit(runner)
        R-)W: ⚡ aboutToStart
        R->>T: create task
        R-)W: ⚡ started
        R->>T: execute
        T->>T: [0..n] progress = v
        T-)W: [0..n] ⚡ sigProgressChanged(v)
        T-->>R: result / exception
        R->>E: raw_future.set_result / set_exception
        E->>E: add_done_callback runs right away (future already done)
        E->>E: _done_callback: stop_watching() (no-op), then _handle_done
        E-)W: ⚡ succeeded / failed
        E-)W: ⚡ finished
        E-->>W: return TaskFuture (already done)

Thread
------

The task runs in a worker thread, which emits the executor signals and the
progress signal itself. Qt queues them to the GUI thread in the order they
were emitted from that single thread, so the order holds without any extra
synchronization.

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
        E->>E: _handle_progess_arg: keep or drop progress
        E->>R: pool.submit(runner)
        R->>R: _wait_ready()
        E-)W: ⚡ submitted
        E->>R: ready_event.set()
        R-)W: 📨 aboutToStart
        R->>T: create task
        R-)W: 📨 started
        R->>T: execute
        T->>T: [0..n] progress = v
        T-)W: [0..n] 📨 sigProgressChanged(v)
        T-->>R: result / exception
        R->>R: raw_future.set_result, done callback (worker thread)
        R->>R: _done_callback: stop_watching() (no-op), then _handle_done
        R-)W: 📨 succeeded / failed
        R-)W: 📨 finished

The ``ready_event`` keeps the worker from starting the task before
``submitted`` has been emitted.

Process
-------

The task runs in a worker process, which cannot emit Qt signals in the parent
nor update the caller's progress object (usually a ``QObject``, which is not
picklable). Instead, parent and child communicate through two
``multiprocessing`` manager queues:

- the queue to the parent:

  - the runner puts ``ToParent.ABOUT_TO_START`` and ``ToParent.STARTED``,
  - the caller's progress object is replaced by a
    :class:`~ewoksorange.gui.concurrency._progress.QueueProgress`, which puts
    each progress value on that same queue.

- the queue to the child: first the decision whether the task may start
  (``ToChild.START`` or a ``StartDenial``), then ``ToChild.REQUEST_STOP`` and
  ``ToChild.ABORT``, read by a thread in the child while the task executes.

In the parent, a single relay thread started by
:meth:`ProcessTaskController.watch() <ewoksorange.gui.concurrency._controllers.process.ProcessTaskController.watch>`
reads the queue and calls the matching callback: it emits ``started``, or sets
the value on the caller's progress object. On ``ToParent.ABOUT_TO_START`` it decides
whether the task may start (it may not once it was cancelled, stopped, aborted
or killed), replies to the child and emits ``aboutToStart`` when allowed. The
relay only starts once ``submitted`` has been emitted, so the child cannot start
the task before that. The decision is always the first message to the child:
stop and abort requests are only put on the queue to the child once the start
was allowed.

.. mermaid::

    sequenceDiagram
        box GUI thread
        participant W as Widget
        participant E as EwoksExecutor
        end
        participant M as Manager (to_parent_queue, to_child_queue)
        box Parent: relay thread
        participant RL as Relay
        end
        box Parent: pool management thread
        participant PM as pebble.ProcessPool mgmt
        end
        box Child process
        participant C as ProcessTaskRunner + Task
        end

        W->>E: submit_task(task, progress?)
        E->>M: create to_parent_queue and to_child_queue
        E->>E: progress replaced by QueueProgress(to_parent_queue), or dropped
        E->>PM: pool.submit(runner) (pickled)
        E-)W: ⚡ submitted
        E->>RL: watch(on_about_to_start, on_started, on_progress)
        RL->>M: get() (blocks)
        PM->>C: run runner
        C->>M: put(ToParent.ABOUT_TO_START), then wait on to_child_queue
        M-->>RL: ToParent.ABOUT_TO_START
        RL->>M: put the decision on to_child_queue
        RL-)W: 📨 aboutToStart, only when allowed
        M-->>C: decision (raise or return when denied)
        C->>C: create task
        C->>M: put(ToParent.STARTED)
        M-->>RL: ToParent.STARTED
        RL-)W: 📨 started
        C->>C: execute
        C->>C: [0..n] progress = v, QueueProgress puts v on to_parent_queue
        RL->>RL: [0..n] get v, on_progress(v): progress = v
        RL-)W: [0..n] 📨 sigProgressChanged(v)
        C-->>PM: result / exception
        PM->>PM: raw_future.set_result, then _done_callback
        PM->>M: stop_watching(): put(ToParent.END)
        M-->>RL: ToParent.END (after all events above)
        RL->>RL: exit
        PM->>RL: join(timeout=5s)
        PM->>PM: _handle_done
        PM-)W: 📨 succeeded / failed
        PM-)W: 📨 finished

The diagram shows the relay reading each event right after it is put; in
practice both run concurrently. What matters is the ordering:

- **One queue, one reader.** All events of a task travel through the same
  first-in first-out queue and are relayed by a single thread, so callbacks
  run in the order the child emitted them.
- **Everything is delivered before completion.** The child puts all its
  events before returning its result, while ``ToParent.END`` is only put by the parent
  once the result is in (in ``_done_callback``). Manager proxy calls are
  synchronous, so every child event is already queued ahead of ``ToParent.END``.
  Waiting for the relay to reach ``ToParent.END`` therefore delivers all of them before
  ``succeeded`` / ``failed`` are emitted.

The relay's lifetime is tied to the task's future, not to a timeout:

- **Prevented from starting.** The child only puts ``ToParent.ABOUT_TO_START``, is
  denied and finishes, so the done callback puts ``ToParent.END``.
- **Crashed child.** The pool sets a ``pebble.ProcessExpired`` error on the
  future and replaces the worker, so the done callback still runs and puts
  ``ToParent.END``.
- **Killed child.** ``TaskFuture.kill()`` cancels the pebble future, which runs
  the done callback right away, in the thread calling ``kill()``, so it puts
  ``ToParent.END``. The pool then terminates the worker and replaces it.
- **Manager shut down.** Reading the queue raises and the relay exits.
- **Long-running task.** The relay keeps waiting, since progress may still
  come. There is deliberately no timeout on reading the queue: a timeout would
  end the relay early and silently drop the events that follow.

``stop_watching()`` itself is bounded: putting ``ToParent.END`` is a single call to the
manager, and the relay thread is joined with a 5 s timeout. That wait only
matters if a receiver connected with ``Qt.DirectConnection`` is slow, since
such a slot runs in the relay thread. With the default (queued) connections,
the relay only posts events to the GUI thread and never blocks.
