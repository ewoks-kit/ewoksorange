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
        Note right of EX: is_running -> True (synchronous)
        EX->>BG: run Task.execute()
        W->>W: progressBarInit()
        Note right of SM: is_active(node) -> True

        BG-->>BG: task runs
        Note right of EX: is_running -> False (in worker thread,<br/>before any signal is delivered)
        BG--)EX: Future done callback
        EX--)W: succeeded/failed (queued across threads)

        Note over W: GUI thread now runs __on_succeeded/__on_failed
        W->>W: propagate_downstream()
        W->>SM: Output.send() for each output
        Note right of SM: has_pending() -> True for downstream nodes
        W->>W: progressBarFinished()
        Note right of SM: is_active(node) -> False

        Note over SM: 100ms timer (re-armed), next node's turn

Node "settledness"
-------------------

``SignalManager`` exposes predicates a caller can use to know whether there
is still work in flight. A node cycles through five states; the same
``Idle -> Queued`` transition applies whether the signal comes from the
initial trigger or from an upstream node's propagation:

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
            is_running == True
            is_active(node) == False
            (submission gap)
        end note
        note right of Running
            is_running == True
            is_active(node) == True
        end note
        note right of Finishing
            is_running == False
            is_active(node) == True
            (outputs not sent yet)
        end note
        note right of Idle
            is_running == False
            is_active(node) == False
        end note

The ``Submitted`` and ``Finishing`` states above are exactly where
:attr:`is_running <ewoksorange.gui.concurrency.executor.EwoksExecutor.is_running>`
and ``is_active(node)`` briefly disagree; see the two guarantees below for
why polling both together is still reliable.

A workflow is fully done once, for every node:

- nothing is queued (not :meth:`signal_manager.has_pending() <ewoksorange.gui.orange_utils.signal_manager.SignalManagerWithScheme.has_pending>`) and

- nothing is executing (not :meth:`signal_manager.is_active(node) <ewoksorange.gui.orange_utils.signal_manager.SignalManagerWithScheme.is_active>`).

The task itself runs on a background thread, but ``is_active(node)`` only
changes when Qt delivers a *queued* cross-thread signal, so it does not
necessarily flip at the exact moment the task actually starts or finishes.
Two ordering guarantees close that gap, so polling ``has_pending()`` and
``is_active(node)`` never gives a false "idle" reading:

- **Start:**
  :attr:`EwoksExecutor.is_running <ewoksorange.gui.concurrency.executor.EwoksExecutor.is_running>`
  flips to ``True`` synchronously at submission time, on the GUI thread —
  before ``is_active(node)`` catches up (which needs the queued
  :attr:`started <ewoksorange.gui.concurrency.executor.EwoksExecutor.started>`
  signal to be delivered first, triggering
  :meth:`progressBarInit() <ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.progressBarInit>`).
  A caller must therefore check *both* ``is_active(node)`` and
  ``task_executor.is_running`` to avoid a false "idle" reading right after
  submission.
- **Finish:** :class:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget` always
  calls
  :meth:`propagate_downstream() <ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.propagate_downstream>`
  **before**
  :meth:`progressBarFinished() <ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.progressBarFinished>`.
  So the moment ``is_active(node)`` becomes ``False``, this widget's outputs
  have already been sent (or invalidated), and any newly pending downstream
  signal is already reflected by ``has_pending()``.

See :meth:`~ewoksorange.gui.canvas.handler.OrangeCanvasHandler.wait_widgets`
for the polling loop that uses these predicates to wait for a workflow to
finish outside of the Orange canvas GUI.
