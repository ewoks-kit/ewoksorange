.. _tuto_first_widget_starting:

Starting my first ewoks orange widget
=====================================

In this chapter we will:

* see how to do a basic connection between an ewoks task and an orangecontrib widget

Setting up ewoksorange
----------------------

Please make sure you already have `ewoksorange` install on your python environment. Else please see `installation`


Defining an ewoks task
----------------------

For this tutorial we would like to add a dedicated interface for the a task performing some data clipping from percentiles.
We already have implemented it with `ewokscore <https://gitlab.esrf.fr/workflow/ewoks/ewokscore>`_.

.. include:: materials/starting/clipdata.py
    :literal:


.. note::
    
    While ``input_model`` and ``output_model`` are optional, using them ensures type consistency and improves integration with Orange (allows link type data checking for example).
    For this tutorial, assume they are defined.

.. hint::

    For simplicity, this tutorial keeps models in the same file as the task. For complex projects please consider defining them in a dedicated file (e.g., ``my_project.models.clip_data``) and import them.


Associate a task to a dedicated orange widget
---------------------------------------------

Now we want to create a widget associated to the task.

There is different ways to define the ewoks tasks execution with orange (see :ref:`Ewoks widgets and execution`).

On this example we will take the ewoks widget doing the processing in a single thread (:ref:`design single thread no stack (OWEwoksWidgetOneThread)`).
Because this will make sure the gui will not freeze with it and we don't need concurrent execution.

Widget 'skeleton' is the following:

.. code-block:: python
    :linenos:

    from ewoksorange.gui.owwidgets.threaded import OWEwoksWidgetOneThread
    from [my_project].tasks.clipdata import ClipDataTask

    class OWClipData(
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

    * `l1`\: import of the required base class for the widget.
    * `l2`\: import of the task to bind with the widget.
    * `l4`\: OW stand for Orange Widget.
    * `l5`\: inheritance with the ewoks orange widget.
    * `l6`\: definition of the ewoks task to bind. This is usually given with the full module path. For example if `RescaleDataTask` is saved in `my_project.tasks.rescale` the value would be `my_project.tasks.rescale.RescaleDataTask`.
    * `l8`\: the name of the widget (will be displayed in the canvas).
    * `l9`\: id from the orange point of view. It should be constant with time to ensure workflow compatibility.
    * `l10`\: tooltip of the widget.


.. tip::

     If Orange is installed, you can preview the widget by running

     .. code:: python

              from Orange.widgets.utils.widgetpreview import WidgetPreview

              WidgetPreview(OWClipData).run()


.. admonition:: Results
    :class: dropdown

    .. include:: materials/starting/clipdata.py
        :literal:

    .. include:: materials/starting/OWClipData.py
        :literal:

Further reading
---------------

:ref:`tuto_first_widget_testing`
