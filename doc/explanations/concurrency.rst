Execution Backends
==================

:class:`~ewoksorange.gui.concurrency.executor.EwoksExecutor` runs a task in one
of three ways (see :class:`~ewoksorange.gui.concurrency.executor.Concurrency`):
in the calling thread, in a thread pool or in a process pool. Whatever the
backend, receivers observe the same order of signals for a task:

``submitted`` → ``aboutToStart`` → ``started`` → progress values →
``aborted`` (if any) → ``succeeded`` / ``failed`` → ``finished``

This page explains how each backend preserves that order. In the diagrams
below, ``progress?`` stands for the optional ``progress`` task argument: it is
only forwarded when the task class is a ``TaskWithProgress``, and dropped
otherwise. Progress steps marked ``[0..n]`` happen once per progress value the
task reports, so never without progress.

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
        E-->>W: submitted
        E->>R: _sync_submit(runner)
        R-->>W: aboutToStart (direct)
        R->>T: create task
        R-->>W: started (direct)
        R->>T: execute
        T->>T: [0..n] progress = v, QProgress emits sigProgressChanged(v) (direct)
        T-->>R: result / exception
        R->>E: raw_future.set_result / set_exception
        E->>E: add_done_callback runs right away (future already done)
        E->>E: _done_callback: stop_watching() (no-op), then _handle_done
        E-->>W: succeeded / failed
        E-->>W: finished
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
        E-->>W: submitted
        E->>R: ready_event.set()
        R-)W: aboutToStart (queued)
        R->>T: create task
        R-)W: started (queued)
        R->>T: execute
        T->>T: [0..n] progress = v, QProgress emits sigProgressChanged(v) (queued)
        T-->>R: result / exception
        R->>R: raw_future.set_result, done callback (worker thread)
        R->>R: _done_callback: stop_watching() (no-op), then _handle_done
        R-)W: succeeded / failed (queued)
        R-)W: finished (queued)

The ``ready_event`` keeps the worker from starting the task before
``submitted`` has been emitted.

Process
-------

The task runs in a worker process, which cannot emit Qt signals in the parent
nor update the caller's progress object (usually a ``QObject``, which is not
picklable). Instead, the child reports its events through a single
``multiprocessing`` manager queue:

- the runner puts ``ABOUT_TO_START`` and ``STARTED``,
- the caller's progress object is replaced by a
  :class:`~ewoksorange.gui.concurrency._progress.QueueProgress`, which puts
  each progress value on that same queue.

In the parent, a single relay thread started by
:meth:`ProcessTaskController.watch() <ewoksorange.gui.concurrency._controllers.process.ProcessTaskController.watch>`
reads the queue and calls the matching callback: it emits ``aboutToStart`` or
``started``, or sets the value on the caller's progress object.

.. mermaid::

    sequenceDiagram
        box GUI thread
        participant W as Widget
        participant E as EwoksExecutor
        end
        participant M as Manager (events_queue)
        box Parent: relay thread
        participant RL as Relay
        end
        box Parent: pool management thread
        participant PM as ProcessPool mgmt
        end
        box Child process
        participant C as ProcessTaskRunner + Task
        end

        W->>E: submit_task(task, progress?)
        E->>M: create events_queue, ready/abort/aborted events
        E->>E: progress replaced by QueueProgress(events_queue), or dropped
        E->>RL: watch(on_about_to_start, on_started, on_progress)
        RL->>M: get() (blocks)
        E->>PM: pool.submit(runner) (pickled)
        E-->>W: submitted
        E->>M: ready_event.set()
        PM->>C: run runner
        C->>M: _wait_ready()
        C->>M: put(ABOUT_TO_START)
        M-->>RL: ABOUT_TO_START
        RL-)W: aboutToStart (queued)
        C->>C: create task
        C->>M: put(STARTED)
        M-->>RL: STARTED
        RL-)W: started (queued)
        C->>C: execute
        C->>C: [0..n] progress = v, QueueProgress puts v on events_queue
        RL->>RL: [0..n] get v, on_progress(v): QProgress emits sigProgressChanged(v) (queued)
        C-->>PM: result / exception
        PM->>PM: raw_future.set_result, then _done_callback
        PM->>M: stop_watching(): put(STOP)
        M-->>RL: STOP (after all events above)
        RL->>RL: exit
        PM->>RL: join(timeout=5s)
        PM->>PM: _handle_done
        PM-)W: succeeded / failed (queued)
        PM-)W: finished (queued)

The diagram shows the relay reading each event right after it is put; in
practice both run concurrently. What matters is the ordering:

- **One queue, one reader.** All events of a task travel through the same
  first-in first-out queue and are relayed by a single thread, so callbacks
  run in the order the child emitted them.
- **Everything is delivered before completion.** The child puts all its
  events before returning its result, while ``STOP`` is only put by the parent
  once the result is in (in ``_done_callback``). Manager proxy calls are
  synchronous, so every child event is already queued ahead of ``STOP``.
  Waiting for the relay to reach ``STOP`` therefore delivers all of them before
  ``succeeded`` / ``failed`` are emitted.

The relay's lifetime is tied to the task's future, not to a timeout:

- **Cancelled while queued.** The child never runs, so the queue only holds
  ``STOP`` and the relay exits immediately. Nothing else is emitted.
- **Child crash.** The pool sets ``BrokenProcessPool`` on the future, so the
  done callback still runs and puts ``STOP``.
- **Manager shut down.** Reading the queue raises and the relay exits.
- **Long-running task.** The relay keeps waiting, since progress may still
  come. There is deliberately no timeout on reading the queue: a timeout would
  end the relay early and silently drop the events that follow.

``stop_watching()`` itself is bounded: putting ``STOP`` is a single call to the
manager, and the relay thread is joined with a 5 s timeout. That wait only
matters if a receiver connected with ``Qt.DirectConnection`` is slow, since
such a slot runs in the relay thread. With the default (queued) connections,
the relay only posts events to the GUI thread and never blocks.
