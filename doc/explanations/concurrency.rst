Execution Backends
==================

:class:`~ewoksorange.gui.concurrency.executor.EwoksExecutor` runs a task in one
of three ways (see :class:`~ewoksorange.gui.concurrency.executor.Concurrency`):
in the calling thread, in a thread pool or in a process pool. Whatever the
backend, receivers observe the same order of signals for a task:

``submitted`` → ``aboutToStart`` → ``started`` → progress values →
``stopRequested`` → ``succeeded`` / ``failed`` → ``finished``

``stopRequested`` is only emitted for a task that was requested to stop. A task
that is cancelled before it starts emits ``submitted`` → ``cancelled`` →
``finished``. A task that is requested to stop before it starts emits
``submitted`` → ``stopRequested`` → ``failed`` → ``finished``. ``finished`` is
the last signal of every submitted task. ``aborted`` and ``killed`` (process
pool only) follow the same rules as ``stopRequested``.

In the ``"thread"`` and ``"process"`` backends, the executor does not emit the
completion signals (``cancelled``, ``stopRequested``, ``aborted``,
``killed``, ``succeeded``, ``failed``, ``finished``) from the callback that
detects the completion. That callback can run in any thread, including the GUI
thread (in ``kill()``), so it emits the internal ``_done`` signal,
which is always queued to the GUI thread. The completion signals are then
emitted in the GUI thread, after the signals of the task that were queued
before.

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
        E->>E: _handle_progress_arg: keep or drop progress
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
        E->>E: _handle_progress_arg: keep or drop progress
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
        R->>R: _done_callback: stop_watching() (no-op)
        R-)E: _done (queued)
        E->>E: _handle_done
        E-->>W: succeeded / failed
        E-->>W: finished

The ``ready_event`` keeps the worker from starting the task before
``submitted`` has been emitted.

Process
-------

The task runs in a worker process, which cannot emit Qt signals in the GUI
process nor update the caller's progress object (usually a ``QObject``, which
is not picklable). The ``ProcessTaskController`` in the GUI process and the
``ProcessTaskRunner`` in the worker process communicate through two
``multiprocessing`` manager queues, one per direction:

- The queue to the controller carries ``ToController.ABOUT_TO_START``,
  ``ToController.STARTED`` and the progress values: the caller's progress
  object is replaced by a
  :class:`~ewoksorange.gui.concurrency._messages.QueueProgress`, which puts
  each progress value on that same queue.
  While the task executes, a sender thread of the runner puts the progress
  values, so that an abort never interrupts the task thread in the middle of
  a queue call.
- The queue to the runner carries the decision whether the task may start
  (``ToRunner.START`` or a ``StartDenial``), then ``ToRunner.REQUEST_STOP``
  and ``ToRunner.ABORT``. ``ToRunner.ABORT`` interrupts the task with a
  ``KeyboardInterrupt``.

In the GUI process, a single relay thread started by
:meth:`ProcessTaskController.watch() <ewoksorange.gui.concurrency._controllers.process.ProcessTaskController.watch>`
reads the queue to the controller and calls the matching callback. On
``ToController.ABOUT_TO_START``, it decides whether the task may start (it may
not once it was cancelled, stopped, aborted or killed), replies to the runner, and
emits ``aboutToStart`` when allowed. On ``ToController.STARTED`` it emits
``started``, and on a progress value it sets the value on the caller's progress
object. The relay only starts once ``submitted`` was emitted, so the runner
cannot start the task before that.

.. mermaid::

    sequenceDiagram
        box GUI thread
        participant W as Widget
        participant E as EwoksExecutor
        end
        participant M as Manager (queues)
        box GUI process: relay thread
        participant RL as Relay
        end
        box GUI process: pebble pool threads
        participant PM as pebble.ProcessPool
        end
        box Worker process
        participant R as ProcessTaskRunner + Task
        end

        W->>E: submit_task(task, progress?)
        E->>M: create the queue to the controller and the queue to the runner
        E->>E: progress replaced by QueueProgress, or dropped
        E->>PM: pool.submit(runner) (pickled)
        E-->>W: submitted
        E->>RL: watch(on_about_to_start, on_started, on_progress)
        RL->>M: get() (blocks)
        PM->>R: run runner
        R->>M: put(ABOUT_TO_START), then wait for the decision
        M-->>RL: ABOUT_TO_START
        RL->>M: put(START) on the queue to the runner
        RL-)W: aboutToStart (queued)
        M-->>R: START
        R->>R: create task
        R->>M: put(STARTED)
        M-->>RL: STARTED
        RL-)W: started (queued)
        R->>R: execute
        R->>R: [0..n] progress = v, QueueProgress puts v on the queue to the controller
        RL->>RL: [0..n] get v, on_progress(v): QProgress emits sigProgressChanged(v) (queued)
        R-->>PM: result / exception
        PM->>PM: raw_future.set_result, then _done_callback
        PM->>M: stop_watching(): put(END)
        M-->>RL: END (after all events above)
        RL->>RL: exit
        PM->>RL: join(timeout=5s)
        PM-)E: _done (queued)
        E->>E: _handle_done
        E-->>W: succeeded / failed
        E-->>W: finished

The diagram shows the relay reading each event right after it is put; in
practice both run concurrently. What matters is the ordering:

- **One queue, one reader.** All events of a task travel through the same
  first-in first-out queue to the controller and are relayed by a single
  thread, so callbacks run in the order the runner put them.
- **Everything is delivered before completion.** The runner puts all its
  events before returning its result, while ``END`` is only put by the
  controller once the result is in (in ``_done_callback``). Manager proxy calls
  are synchronous, so every event of the runner is already queued ahead of
  ``END``. Waiting for the relay to reach ``END`` therefore delivers all of
  them before ``succeeded`` / ``failed`` are emitted.
- **The start decision comes first.** Stop requests and aborts are only put on the queue
  to the runner once the start was allowed, so the runner always reads the
  decision first.

The relay's lifetime is tied to the task's future, not to a timeout:

- **Cancelled or stopped while queued.** The runner only puts
  ``ABOUT_TO_START``, is denied and returns or raises, so the done callback
  runs and puts ``END``.
- **Worker crash.** The pool sets ``pebble.ProcessExpired`` on the future and
  replaces the worker process, so the done callback still runs and puts
  ``END``.
- **Killed worker.** ``kill()`` cancels the future of the pool, which runs the
  done callback right away, in the thread calling ``kill()``. When a worker
  already picked up the task, the pool terminates that worker process and
  replaces it.
- **Manager shut down.** Reading the queue raises and the relay exits.
- **Long-running task.** The relay keeps waiting, since progress may still
  come. There is deliberately no timeout on reading the queue: a timeout would
  end the relay early and silently drop the events that follow.

``stop_watching()`` itself is bounded: putting ``END`` is a single call to the
manager, and the relay thread is joined with a 5 s timeout. That wait only
matters if a receiver connected with ``Qt.DirectConnection`` is slow, since
such a slot runs in the relay thread. With the default (queued) connections,
the relay only posts events to the GUI thread and never blocks.
