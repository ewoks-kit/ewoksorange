.. _tuto_first_widget_starting:

Starting my first ewoks orange widget
=====================================

Setting up ewoksorange
----------------------

Please make sure you already have `ewoksorange` install on your python environment. Else please see `installation`


Defining an ewoks task
----------------------

For this tutorial we would like to add a dedicated interface for the a task performing some data clipping from percentiles.
We already have implemented it with `ewokscore <https://gitlab.esrf.fr/workflow/ewoks/ewokscore>`_.

.. code-block:: python

    from ewokscore.task import Task
    import numpy

    class ClipDataTask(
        Task,
        input_names=["data", "percentiles"],
        output_names=["data"],
    ):
        """
        Task to rescale 'data' (numpy array) to the given percentiles.
        """

        def run(self):
            data = self.inputs.data
            # compute data min and max
            percentiles = self.inputs.percentiles
            assert isinstance(percentiles, tuple) and len(percentiles) == 2, "incoherent input"
            assert percentiles[0] <= percentiles[1], "incoherent percentiles value"

            self.outputs.data = numpy.clip(
                data,
                a_min=numpy.percentile(data, percentiles[0]),
                a_max=numpy.percentile(data, percentiles[1]),
            )


Associate a task to a dedicated orange widget
---------------------------------------------

Now we want to create a widget associated to the task.

There is different ways to define the ewoks tasks execution with orange (see :ref:`Ewoks widgets and execution`).

On this example we will take the ewoks widget doing the processing in a single thread (:ref:`design single thread no stack (OWEwoksWidgetOneThread)`).
Because this will make sure the gui will not freeze with it and we don't need concurrent execution.

Widget 'skeleton' is the following:

.. code-block:: python
    :linenos:

    class ClipDataOW(
        OWEwoksWidgetOneThread,
        ewokstaskclass=ClipDataTask,
    ):
        name = "rescale data"
        id = "orange.widgets.my_project.ClipDataTask"
        description = (
            "widget to clip data (numpy array) within a percentile range."
        )
        pass


.. hint::

    * l1: OW stand for Orange Widget
    * l2: inheritance with the ewoks orange widget
    * l3: definition of the ewoks task to bind. This is usually given with the full module path. For example if `RescaleDataTask` is saved in `my_project.tasks.rescale` the value would be `my_project.tasks.rescale.RescaleDataTask`
    * l5: the name of the widget (will be displayed in the canvas)
    * l6: id from the orange point of view. It should be constant with time to make insure workflow compatibility. 
    * l7: tooltip of the widget
