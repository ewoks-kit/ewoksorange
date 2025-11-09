Specifying different inputs/outputs for Orange widgets
------------------------------------------------------


Adding inputs/outputs to Orange widgets
=======================================

In advanced designs of Orange widgets, it can happen that the widget (GUI) does more work than simply
executing the Ewoks task. For example, the Ewoks task could take a filename as input and the Orange
widget could provide a GUI with a file browser to select this filename.

In this case, it may be useful to specify additional parameters **only for the Orange widget**
(in our example,  the Orange widget could take a root directory as input to know where the file
browser should start browsing, but the Ewoks task does not need to have this input).

For this, we can define additional inputs directly in the Orange widget using the
`Inputs class <https://orange3.readthedocs.io/projects/orange-development/en/latest/widget.html#input-output-signal-definitions>`_:

.. code-block:: python

    from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
    from ewokscore.tests.examples.tasks.sumtask import SumTask
    from ewoksorange.gui.orange_utils.signals import Input


    class OrangeInputExample(
        OWEwoksWidgetOneThread,
        ewokstaskclass=SumTask,
    ): 

        class Inputs:
            root_directory = Input("root_directory", str, ewoksname="root_directory")

The first two required arguments are the Orange name and type of the inputs. The `ewoksname` is optional
and defaults to the attribute name in the `Inputs` class.

The input will then be available as a possible choice when connecting another widget to this widget's inputs,
in addition of the Ewoks task (`SumTask` here) inputs.

The value of inputs created this way can be retrieved as arguments of the class methods by decorating the
methods with `@Inputs.<input_name>`

.. code-block:: python

    class OrangeInputExample(
        ...
    ):
        ...

        @Inputs.root_directory
        def deal_with_root_directory(self, root_dir: str)
            # root_dir will have the value of the root_directory input in this method
            # ...

Similarly, additional custom outputs can created this way using the
`Outputs class <https://orange3.readthedocs.io/projects/orange-development/en/latest/widget.html#input-output-signal-definitions>`_:

.. code-block:: python

    from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
    from ewokscore.tests.examples.tasks.sumtask import SumTask
    from ewoksorange.gui.orange_utils.signals import Output


    class OrangeOutputExample(
        OWEwoksWidgetOneThread,
        ewokstaskclass=SumTask,
    ): 

        class Outputs:
            filename = Output("filename", str, ewoksname="filename")

The first two required arguments are the Orange name and type of the inputs. The `ewoksname` is optional
and defaults to the attribute name in the `Inputs` class.

The output will then be available as a possible choice when connecting this widget to another widget's inputs.

The output value must be updated manually via the `.send` function:

.. code-block:: python

    class OrangeOutputExample(
        ...
    ):
        ...

        def update_output(self, new_value: str):
            self.Outputs.filename.send(new_value)


Hiding Ewoks inputs/outputs from Orange widgets
===============================================

.. note:: 

    Added in version 0.4.0

When linking two Orange tasks, it is possible to link any output of the source Ewoks task to any
input of the target Ewoks task.

.. image:: img/data_mapping.png
    :alt: A image of a link between two tasks showing one output choice on the left and multiple input choices on the right.


To hide some of these inputs/outputs, we need to specify their name in the
``_ewoks_inputs_to_hide_from_orange``/``_ewoks_outputs_to_hide_from_orange`` class members.

In this example, we hide inputs from the target task:

.. code-block:: python

    class RawDataScreenshotCreatorOW(
        ...
    ):
        _ewoks_inputs_to_hide_from_orange = (
            "__process__",
            "raw_projections_required",
            "raw_projections_each",
            "raw_darks_required",
            "raw_flats_required",
        )

        ...

We can then verify that the specified inputs are absent when trying to using this task as a link target:

.. image:: img/data_mapping_with_hidden_inputs.png
    :alt: A image of a link between two tasks showing one output choice on the left and one input choice on the right.
