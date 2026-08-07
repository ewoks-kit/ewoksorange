Execution Lifecycle
====================

This page explains how a workflow actually runs on the Orange canvas: how the
:class:`SignalManager <ewoksorange.gui.orange_utils.signal_manager.SignalManagerWithScheme>`
schedules node updates, how an Ewoks-Orange widget executes its task, and how
outputs propagate to downstream widgets. Native Orange widgets (``OWWidget``)
and Ewoks widgets (:class:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget`)
share the same scheduling machinery; only the "how does *this* widget execute
its work" step differs.

Key players
-----------

- **SignalManager** (``orangecanvas``/``orangewidget``): owns the queue of
  signals to deliver and a single coalescing 100 ms timer that drives
  delivery. It never executes widget code itself; it only calls
  :meth:`handleNewSignals() <ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.handleNewSignals>`
  once all of a node's inputs have been updated.
- **OWEwoksBaseWidget** (:class:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget`,
  ``ewoksorange``): implements ``handleNewSignals()`` by executing the bound
  Ewoks task and, once done, propagating outputs (or invalidation, on
  failure) through
  :meth:`propagate_downstream() <ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.propagate_downstream>`.
- **EwoksExecutor** (:class:`~ewoksorange.gui.concurrency.executor.EwoksExecutor`,
  ``ewoksorange``): receives submitted tasks
  (:meth:`submit_task() <ewoksorange.gui.concurrency.executor.EwoksExecutor.submit_task>`)
  and runs them synchronously or on a background thread/process, re-entering
  the GUI thread through Qt signals
  (:attr:`~ewoksorange.gui.concurrency.executor.EwoksExecutor.started`,
  :attr:`~ewoksorange.gui.concurrency.executor.EwoksExecutor.succeeded`,
  :attr:`~ewoksorange.gui.concurrency.executor.EwoksExecutor.failed`).

One execution cycle
--------------------

.. mermaid::

    sequenceDiagram
        participant SM as SignalManager (GUI thread)
        participant W as OWEwoksBaseWidget (GUI thread)
        participant EX as EwoksExecutor
        participant BG as Background thread

        Note over SM: 100ms timer fires, node is next in line
        SM->>W: handleNewSignals()
        W->>EX: submit_task()
        Note right of W: has_pending_task() -> True (synchronous)
        EX->>BG: run Task.execute()
        W->>W: progressBarInit()
        Note right of SM: is_active(node) -> True

        BG-->>BG: task runs
        Note right of BG: has_pending_task() -> still True<br/>(succeeded/failed not delivered yet)
        BG--)EX: Future done callback
        EX--)W: succeeded/failed (queued across threads)

        Note over W: GUI thread now runs __on_succeeded/__on_failed
        W->>W: propagate_downstream()
        W->>SM: Output.send() for each output
        Note right of SM: has_pending() -> True for downstream nodes
        W->>W: progressBarFinished()
        Note right of SM: is_active(node) -> False
        Note right of W: has_pending_task() -> False

        Note over SM: 100ms timer (re-armed), next node's turn

The diagram shows the default case, where the task runs on a background
thread. The other backends only change who runs the task:

``concurrency="sync"``
    Every step runs on the GUI thread, inside the ``submit_task()`` call, so
    ``handleNewSignals()`` only returns once the outputs have been propagated.
``concurrency="process"``
    A worker process runs the task. Its lifecycle events and progress travel
    back over ``multiprocessing`` proxies, relayed onto the GUI thread by
    :class:`~ewoksorange.gui.concurrency._controllers.process.ProcessTaskController`.

Node "settledness"
-------------------

There is no single "is this workflow done?" flag. "Settled" is spread
across three independent flags, each owned by a different layer, each
covering a different slice of one widget's execution:

:meth:`has_pending_task() <ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.has_pending_task>` (widget)
    True while a task submission hasn't reached its GUI-thread completion
    callback yet.
:meth:`is_active(node) <ewoksorange.gui.orange_utils.signal_manager.SignalManagerWithScheme.is_active>` (canvas)
    True while the widget's progress bar is running.
:meth:`has_pending() <ewoksorange.gui.orange_utils.signal_manager.SignalManagerWithScheme.has_pending>` (canvas)
    True while some node has a signal scheduled but not yet delivered.

A workflow is settled only once **every one** of these reads "not busy",
for every node and widget. A node cycles through five states on the way
there; the same ``Idle -> Queued`` transition applies whether the signal
comes from the initial trigger or from an upstream node's propagation:

.. mermaid::

    stateDiagram-v2
        [*] --> Idle

        Idle --> Queued: Output.send() schedules<br/>a signal for this node
        Queued --> Submitted: 100ms timer fires,<br/>process_node() calls<br/>handleNewSignals()
        Submitted --> Running: queued 'started' signal delivered,<br/>progressBarInit() runs
        Running --> Finishing: task completes<br/>on the background thread
        Finishing --> Idle: queued 'succeeded'/'failed' delivered,<br/>propagate_downstream() sends outputs,<br/>then progressBarFinished() runs

        note right of Queued
            has_pending() == True
        end note
        note right of Submitted
            has_pending_task() == True
            is_active(node) == False
            (submission gap)
        end note
        note right of Running
            has_pending_task() == True
            is_active(node) == True
        end note
        note right of Finishing
            has_pending_task() == True
            is_active(node) == True
            (outputs not sent yet)
        end note
        note right of Idle
            has_pending_task() == False
            is_active(node) == False
        end note

The ``Submitted`` and ``Finishing`` states are exactly where a naive
single-flag check would be fooled: the task's real state and what one
flag reports can momentarily disagree. Checking all three together is
only safe because of one rule, applied twice below: **a flag may only
switch to "not busy" once whatever sits downstream of it already
reflects the change** — never the other way around.

1. ``has_pending()`` before ``is_active(node)``. Sending a task's
   outputs
   (:meth:`propagate_downstream() <ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.propagate_downstream>`)
   is what schedules delivery to downstream nodes, flipping
   ``has_pending()`` to ``True`` — and that call always happens
   *before*
   :meth:`progressBarFinished() <ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.progressBarFinished>`
   clears ``is_active(node)``. So the moment ``is_active(node)`` is
   observed ``False``, any output this widget just produced is already
   visible through ``has_pending()``.

2. ``is_active(node)`` before ``has_pending_task()``. Both calls
   above run *inside* the widget's GUI-thread ``succeeded``/``failed``
   callback — the same callback that finally clears
   ``has_pending_task()``. That callback executes as one
   uninterrupted, non-reentrant step on the GUI thread (the same thread
   `wait_widgets`-style polling runs on), so a poller can only ever see
   it from before it starts or after it has fully finished — never
   midway. So the moment ``has_pending_task()`` is observed
   ``False``, guarantee 1 has already played out too: ``is_active(node)``
   is already ``False`` and ``has_pending()`` already reflects it.

Chaining the two: checking ``has_pending_task()`` alone would be
enough to know the other two are settled — but native ``OWWidget``\ s
have no such flag, so ``is_active(node)`` is still checked directly for
every node, and ``has_pending()`` for the signal manager as a whole.

See :meth:`~ewoksorange.gui.canvas.handler.OrangeCanvasHandler.wait_widgets`
for the polling loop that checks all three flags together to wait for a
workflow to finish outside of the Orange canvas GUI.
