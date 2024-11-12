My first orange widget for ewoks
================================

In this tutorial we will explain you how to create your first orange widget for an ewoks task.


.. important::

     prerequisites: we consider that you are already fluent in python and experienced with ewoks and qt concepts.


Defining an ewoks task
----------------------

For this tutorial we would like to add

.. code-block:: python

    from ewokscore.task import Task
    import numpy


    class RescaleDataTask(
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
            data_min = numpy.percentile(data, percentiles[0])
            data_max = numpy.percentile(data, percentiles[1])

            self.outputs.data = self.rescale_data(
                data=data,
                data_min=data_min,
                data_max=data_max,
            )

        def rescale_data(data, new_min, new_max, data_min=None, data_max=None):
            if data_min is None:
                data_min = numpy.min(data)
            if data_max is None:
                data_max = numpy.max(data)
            return (new_max - new_min) / (data_max - data_min) * (data - data_min) + new_min


Associate a task to a dedicated orange widget
---------------------------------------------

Here we want to create a widget which contains two `QSlider <https://doc.qt.io/qt-6/qslider.html>`_. One for each percentiles.

* when the 'percentiles' inputs arrive it will update the sliders
* when the data arrives it will execute the task and provide 'data' to the next widget

There is different ways to define the ewoks tasks execution with orange (see :ref:`Ewoks widgets and execution`).

On this example we will take the ewoks widget doing the processing in a single thread (:ref:`design single thread no stack (OWEwoksWidgetOneThread)`).
Because this will make sure the gui will not freeze with it and we don't need concurrent execution.

Widget 'skeleton' is the following:

.. code-block:: python
    :linenos:

    class RescaleDataOW(
        OWEwoksWidgetOneThread,
        ewokstaskclass=RescaleDataTask,
    ):
        name = "rescale data"
        id = "orange.widgets.my_project.RescaleDataWidget"
        description = (
            "widget to rescale data (numpy array) within a percentile range."
        )
        pass


.. hint::

    * l1: OW stand for Orange Widget
    * l2: inheritance with the ewoks orange widget
    * l3: definition of the ewoks task to bind. This is usually given with the full module path. For example if `RescaleDataTask` is saved in `my_project.tasks.rescale` the value would be `my_project.tasks.rescale.RescaleDataTask`
    * l5: the name of the widget (will be displayed in the canvas)
    * l6: id from the orange point of view. It should be constant with time to make insure workflow compatibility. 
    * l7: tooltip of the widget


How to test this first widget ?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Include the task in an `orangecontrib` module.

Orange offers a mechanism to include widget to the orange canvas. For this your library must offer an 'orangecontrib' module.
For this you can refer to the :ref:`Starting a new project from scratch` chapter.

If your project is correctly configured you should see the widget appearing:

.. image:: img/my_first_widget/first_discovery.png

.. note:: in this example we have an empty project with orange installed. The `RescaleDataOW` has been added in a `Test Tuto` orangecontrib.

.. hint:: 

    `ewoks-canvas` is automatically launching the widget discovery. If you are using orange-canvas instead you might need to use the `--force-discovery` option.

.. warning::

    each Orange widget should be in a dedicated file. Else orange parsing will fail.
