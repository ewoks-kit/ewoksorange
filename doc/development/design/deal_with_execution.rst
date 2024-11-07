Deal with execution
===================

There are several ways of defining how your Orange Widget will handle the execution of its associated Ewoks task.

* :ref:`design qt main thread`: simple, robust. Long processings can prevent the GUI from responding.
* :ref:`design single thread no stack`: execution is separate from the GUI thread. Can only handle one task at once.
* :ref:`design several thread`: execution is separate from the GUI thread. Can handle multiple tasks at once. Cannot give information on task progress.
* :ref:`design single thread and stack`: execution is separate from the GUI thread. Can give information on task progress.
* :ref:`design free implementation`: for expert users who want to handle the execution themselves.

The choice of design depends on your use case: for example, if you deal with small processing times, the first design (the simplest one) is the best. Other designs allow more flexibility but are more complex. 


.. _design qt main thread:

Execute the associated Ewoks task in the Qt main thread
-------------------------------------------------------

This is the the simplest case and the most robust one.

To use it, make your Orange widget inherit from :class:`OWEwoksWidgetNoThread` and specify the ewoks task to execute in `ewokstaskclass`

.. code-block:: python

    from ewoksorange.bindings import OWEwoksWidgetNoThread
    from ewokscore.tests.examples.tasks.sumtask import SumTask

    class OWSumTask(
        OWEwoksWidgetNoThread,
        ewokstaskclass=SumTask,
    ):
        pass

This will trigger the execution of the method ``run()`` of the Ewoks task :class:`SumTask` when a signal is received.

In this case, the :class:`SumTask` is defined as

.. code-block:: python

    class SumTask(
        Task, input_names=["a"], optional_input_names=["b"], output_names=["result"]
    ):
        def run(self):
            pass


Each input/output in ``input_names``, ``optional_input_names`` and ``output_names`` will be converted to Orange `Inputs/Outputs <https://orange3.readthedocs.io/projects/orange-development/en/latest/widget.html#input-output-signal-definitions>`_ by the :class:`OWEwoksWidgetNoThread` constructor.


.. note:: 
    
    The inputs and outputs of the Orange widget, that can be linked to other widgets, are the same as the ones of the underlying Ewoks task (in this case ``SumTask``). 
    
    See `this page for how to define additional inputs/outputs for the Orange widget <different_inputs_outputs>`_. 

.. warning:: 
    
    Since the processing and display are done in the same thread, the processing can block the GUI freezing the Orange widget. 
    
    If this is a problem (e.g. long processing), look at the other designs.

.. _design single thread no stack:

Execute the associated Ewoks task in a single dedicated thread
----------------------------------------------------------------

The Ewoks task can be run in a different thread than the main Qt/display thread. 

For this, make the Orange widget inherit from :class:`OWEwoksWidgetOneThread`


.. code-block:: python

    class SumListOneThread(
        OWEwoksWidgetOneThread,
        ewokstaskclass=SumList,
    ):

        name = "SumList one thread"

        description = "Sum all elements of a list using at most one thread"

        category = "esrfWidgets"

        want_main_area = False



The Orange widget is holding a processing thread (`_processingThread`) that will execute the `ewokstaskclass`.

.. note:: 
    
    The thread can only execute one task at a time: it will refuse to execute further tasks if the current task is still executing. 
    
    The other designs below allow to circumvent this.

.. note:: When the task is executing, a spinning wheel with progress in percentage is shown in the GUI.
          To make sure the progress number gets update, make sure the Ewoks task is derived from `TaskWithProgress`
          instead of `Task` and the progress is updated in the run method. Otherwise the progress stays
          at `0%` until the task is finished.


.. _design several thread:

Execute each Ewoks task in a dedicated thread per task
------------------------------------------------------

You can have an Orange widget that will create a new thread for each task execution.

For this, make your Orange widget inherit from the :class:`OWEwoksWidgetOneThreadPerRun` widget

.. code-block:: python

    from ewoksorange.bindings import OWEwoksWidgetOneThreadPerRun
    from ewoksorange.tests.examples.tasks import SumList2

    class SumListSeveralThread(
        OWEwoksWidgetOneThreadPerRun,
        ewokstaskclass=SumList2,
    ):

        name = "SumList on several threads"

        description = "Sum all elements of a list using a new thread for each sum"

        category = "esrfWidgets"

        want_main_area = False



.. _design single thread and stack:

Execute Ewoks tasks in dedicated threads handled with a stack
-------------------------------------------------------------

Last design for which we propose an automatic binding is an Orange widget containing a Stack.
The stack is associated with a processing thread and has a first in first out (FIFO) behavior.

To access it you can create a widget inheriting from :class:`OWEwoksWidgetWithTaskStack` widget

.. code-block:: python

    from ewoksorange.bindings import OWEwoksWidgetWithTaskStack
    from ewoksorange.tests.examples.tasks import SumList3

    class SumListWithTaskStack(
        OWEwoksWidgetWithTaskStack,
        ewokstaskclass=SumList3,
    ):
        name = "SumList with one thread and a stack"
        description = "Sum all elements of a list using a thread and a stack"

        category = "esrfWidgets"

        want_main_area = False


The :class:`SumListWithTaskStack` holds an instance of `progress` in its task arguments.

.. _design free implementation:


Handling everything yourself
----------------------------

In some cases you might want to execute one :class:`Task` with Ewoks and another with Orange.

For this, inherit directly from :class:`OWWidget` and provide the `ewokstaskclass` pointing to the Task to be executed by ewoks.

.. code-block:: python

    from Orange.widgets.widget import OWWidget

    class SumListFreeImplementation(
        OWWidget,
    ):
        ewokstaskclass=ewokscore.tests.examples.tasks.sumtask.SumTask


Then you can define standard Orange `Input` and `Output`:

.. code-block:: python

    class SumListFreeImplementation(
        OWWidget,
    ):
        class Inputs:
            list_ = Input("list", list)

        class Outputs:
            sum_ = Output("sum", float)

`Inputs` and `Outputs` can be retrieved and used using the same strategies described in the `additional inputs/outputs page <different_inputs_outputs>`_

.. code-block:: python

    @Inputs.list_
    def compute_sum(self, iterable):
        ...

    def _processingFinished(self):
        ...
        self.Outputs.sum_.send(...)


