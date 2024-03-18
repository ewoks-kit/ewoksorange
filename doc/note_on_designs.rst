Note on designs
===============

There is several design possible to define your Orange Widget and insure compatibility with ewoks orange.

* :ref:`design qt main thread`
* :ref:`design single thread no stack`
* :ref:`design several thread`
* :ref:`design single thread and stack`
* :ref:`design free implementation`

.. _design qt main thread:

Processing `ewokstaskclass` on the Qt main thread
-------------------------------------------------

This is the the simplest case and the most robust one.
This is the designed used in the `ewoks example 1 addon`.

On this case we made Orange Widget inherit from :class:`OWEwoksWidgetNoThread` and with we define the ewoks :class:Task to be used.

.. code-block:: python

    from ewoksorange.bindings import OWEwoksWidgetNoThread
    from ewoksorange.gui.parameterform import ParameterForm
    from ewokscore.tests.examples.tasks.sumtask import SumTask

    class OWSumTask(
        OWEwoksWidgetNoThread,
        ewokstaskclass=SumTask,
    ):
        pass

This will enforce the execution of the :class:`Task`.run() when a signal is received.

The :class:`SumTask` is defined as :

.. code-block:: python

    class SumTask(
        Task, input_names=["a"], optional_input_names=["b"], output_names=["result"]
    ):
        def run(self):
            pass


Each input_names, optional_input_names and output_names will be converted to orange InputSignal, OutputSignal by the :class:`OWEwoksWidgetNoThread` constructor.


.. note:: the Input and Output values must be defined in SumTask

.. warning:: As both processing and display are done in the main thread this will bring gui freeze. If your processing takes time wnd if you want to avoid gui freeze look at other proposed designs.

.. _design single thread no stack:

Processing `ewokstaskclass` on a single (dedicated) thread without stack
------------------------------------------------------------------------

If you want to have a single thread that will process the ewoks.task then you can inherite from :class:`OWEwoksWidgetOneThread`

This is what is done in the `ewoks example 2 addon` class: :class:`SumListOneThread`

You just have to provide task description and link to the ewoks task class:

.. code-block:: python

    class SumListOneThread(
        OWEwoksWidgetOneThread,
        ewokstaskclass=SumList,
    ):

        name = "SumList one thread"

        description = "Sum all elements of a list using at most one thread"

        category = "esrfWidgets"

        want_main_area = False


The Orange widget is containing a processing thread (`_processingThread`) that will execute the `ewokstaskclass`.

.. note:: if a request for processing is done when the thread is already processing it will refuse the processing request. See other design for more advance use case.

.. note:: TODO: speak about progress.


.. _design several thread:

One (dedicated) thread per task no stack
----------------------------------------

You can have an Orange widget that will create a new thread for each new `run`.

For this you should inherit from the :class:`OWEwoksWidgetOneThreadPerRun` widget like this done by the :class:`SumListSeveralThread` of `ewoks example 2 addon`

.. code-block:: python

    class SumListSeveralThread(
        OWEwoksWidgetOneThreadPerRun,
        ewokstaskclass=SumList2,
    ):

        name = "SumList on several thread"

        description = "Sum all elements of a list using a new thread for each" "summation"

        category = "esrfWidgets"

        want_main_area = False


.. note:: when a new thread is created each time a processing is requested this usually prevent from providing a progress.

.. _design single thread and stack:

One dedicated thread for the task and with a stack
--------------------------------------------------

Last design for which we propose an automatic binding is an Orange widget containing a Stack.
The stack is associated with a processing thread and has a first in first out (FIFO) behavior.

To access it you can create a widget inheriting from :class:`OWEwoksWidgetWithTaskStack` widget.
This is what is on in `ewoks example 2 addon` / :class:`SumListWithTaskStack`

.. code-block:: python

    class SumListWithTaskStack(
        OWEwoksWidgetWithTaskStack,
        ewokstaskclass=SumList3,
    ):
        name = "SumList with one thread and a stack"

        description = "Sum all elements of a list using a thread and a stack"

        category = "esrfWidgets"

        want_main_area = False


The SumListWithTaskStack also include an instance of `QProgress`. So you will be able to display the progress of each task.

.. _design free implementation:


Handling everything yourself
----------------------------

In some cases you might want to execute one :class:`Task` with ewoks and another with orange.

Here the simplest way is to inherit directly from :class:`OWWidget` and provide the `ewokstaskclass` pointing to the Task to be executed by ewoks when converted.

.. code-block:: python

    from Orange.widgets.widget import OWWidget
    import ewokscore.tests.examples.tasks.sumtask import SumTask

    class SumListFreeImplementation(
        OWWidget,
    ):
        ewokstaskclass=ewokscore.tests.examples.tasks.sumtask.SumTask


Then you can define standard orange `Input` and `Output` to connect it to the workflow.

.. code-block:: python

    class SumListFreeImplementation(
        OWWidget,
    ):
        class Inputs:
            list_ = Input("list", list)

        class Outputs:
            sum_ = Output("sum", float)

As usual `Inputs` and `Outputs` have to be connected somehow:

.. code-block:: python

    @Inputs.list_
    def compute_sum(self, iterable):
        ...

    def _processingFinished(self):
        ...
        self.Outputs.sum_.send(...)


Orange will use the `@Inputs.[input]` decorator and `Outputs.output` to insure connection between widget.
Ewoks will use the provided `ewokstaskclass` to know which class to execut and the `INPUT_NAMES`, `OUTPUT_NAMES` to insure connection between classes.
