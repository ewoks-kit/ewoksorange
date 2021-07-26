Note on designs
===============

There is two ways of providing an orange add-on with ewoks orange in order to keep a complete compatibility between the two:

* :ref:`design 1`
* :ref:`design 2`

.. _design 1:

Inheriting from :class:`OWEwoksWidget` and use `ewokstaskclass` instance directly
---------------------------------------------------------------------------------

This is the default design to Be used.
This is the designed used in the `ewoks example 1 addon`.

On this case we made Orange Widget inherit from :class:`OWEwoksWidget` and with we define the ewoks :class:Task to be used.

.. code-block:: python

    from ewoksorange.bindings import OWEwoksWidget
    from ewoksorange.gui.parameterform import ParameterForm
    from ewokscore.tests.examples.tasks.sumtask import SumTask

    class Adder1(
        OWEwoksWidget,
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


Each input_names, optional_input_names and output_names will be converted to orange InputSignal, OutputSignal by the :class:`OWEwoksWidget` constructor.


.. warning:: the Input and Output values must be defined in SumTask

.. _design 2:

Inheriting from :class:`Registered` and use another processing functions / class...
-----------------------------------------------------------------------------------

In some cases you might want to execute one :class:`Task` with ewoks and another with orange.
This is the design used in the `ewoks example 2 addon`.

This can be the case for example if you want to have a ewoks Task 100% free of any gui import (as Qt) and have some interaction / progress... with from the orange canvas.
In this case the created OWWidget will be more a "container" of Task than a Task itself. But this will be "hide" to ewoks.

Here the simplest way is to inherit this time from :class:`Registered` and provide the `ewokstaskclass` pointing to the Task to be executed by ewoks when converted.
And as "usual" this should also inherit from :class:`OWWidget`

.. code-block:: python

    from ewokscore.registration import Registered
    from Orange.widgets.widget import OWWidget
    import ewokscore.tests.examples.tasks.sumtask import SumTask

    class SumList(
        OWWidget,
        Registered,
    ):
        ewokstaskclass=ewokscore.tests.examples.tasks.sumtask.SumTask


Then you can define standard orange `Input` and `Output` to connect it to the workflow.

.. code-block:: python

    class SumList(
        OWWidget,
        Registered,
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


To test the example in action open the ewoksorange/test/examples/orangecontrib/tutorials/sumlist_tutorial.ows file within the add-on activated.

This way of insuring connection with Registered insure a safe conversion to ewoks.
But of course no OWWidget will be executed this time but the `ewokstaskclass`.

