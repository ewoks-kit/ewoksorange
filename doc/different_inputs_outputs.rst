Specifying different inputs/outputs for Orange widgets
------------------------------------------------------

In advanced designs of Orange widgets, it can happen that the widget (GUI) does more work than simply executing the Ewoks task. For example, the Ewoks task could take a filename as input and the Orange widget could provide a GUI with a file browser to select this filename.

In this case, it may be useful to specify additional parameters **only for the Orange widget** (in our example,  the Orange widget could take a root directory as input to know where the file browser should start browsing, but the Ewoks task does not need to have this input).

For this, we can define additional inputs directly in the Orange widget using the `Inputs class <https://orange3.readthedocs.io/projects/orange-development/en/latest/widget.html#input-output-signal-definitions>`_:

.. code:: python

    from ewoksorange.bindings import OWEwoksWidgetNoThread
    from ewokscore.tests.examples.tasks.sumtask import SumTask
    from ewoksorange.gui.orange_imports import Input


    class OrangeInputExample(
        OWEwoksWidgetOneThread,
        ewokstaskclass=SumTask,
    ): 

        class Inputs:
            root_directory = Input("root_directory", str) # Note that the input type must be specified

The input will then be available as a possible choice when connecting another widget to this widget's inputs, in addition of the Ewoks task (`SumTask` here) inputs.

The value of inputs created this way can be retrieved as arguments of the class methods by decorating the methods with `@Inputs.<input_name>`

.. code:: python

    class OrangeInputExample(
        ...
    ):
        ...

        @Inputs.root_directory
        def deal_with_root_directory(self, root_dir: str)
            # root_dir will have the value of the root_directory input in this method
            # ...

Similarly, additional custom outputs can created this way using the  `Outputs class <https://orange3.readthedocs.io/projects/orange-development/en/latest/widget.html#input-output-signal-definitions>`_:

.. code:: python

    from ewoksorange.bindings import OWEwoksWidgetNoThread
    from ewokscore.tests.examples.tasks.sumtask import SumTask
    from ewoksorange.gui.orange_imports import Input


    class OrangeOutputExample(
        OWEwoksWidgetOneThread,
        ewokstaskclass=SumTask,
    ): 

        class Outputs:
            filename = Output("filename", str) # Note that the output type must be specified

The output will then be available as a possible choice when connecting this widget to another widget's inputs.

The output value must be updated manually via the `.send` function:

.. code:: python

    class OrangeOutputExample(
        ...
    ):
        ...

        def update_output(self, new_value: str):
            self.Outputs.filename.send(new_value)
            