Use ``ParameterForm`` to easily create Orange widget forms
----------------------------------------------------------

Often, an Orange widget boils down to a form to specify inputs for its associated Ewoks task.

For this common use case, `ewoksorange` provides a ``ParameterForm`` class. Once instantiated, it can generate graphical input elements based on the given input name and types.

For example, let's take a simple Ewoks task ``SumList`` and say we want to write an Orange widget that will allow the user to specify the inputs of this task.

.. code:: python 

    from ewokscore.task import Task


    class SumList(
        Task,
        input_names=["list"],
        optional_input_names=["delay"],
        output_names=["sum"],
    ):
        """Add items from a list"""

        def run(self):
            if self.inputs.list is None:
                raise ValueError("list should be provided")
            if self.inputs.delay:
                delay = self.inputs.delay
            else:
                delay = 0
            sum_ = 0
            for i_elmt, elmt in enumerate(self.inputs.list):
                sum_ += elmt
                _sleep(delay)
            self.outputs.sum = sum_

This task takes a ``list`` as input and iterates over it to sum its elements with an optional ``delay``. We then want the Orange widget to provide us two GUI elements: one textbox to specify the list, and a numeric spinbox to specify the delay.

The Orange widget will then look like this:

.. code:: python

    import json
    from ewoksorange.bindings import OWEwoksWidgetNoThread
    from ewoksorange.gui.parameterform import ParameterForm
    from ewokscore.tests.examples.tasks.sumlist import SumList

    class OWSumList(
        OWEwoksWidgetNoThread,
        ewokstaskclass=SumList,
    ):
        def __init__(self):
            super().__init__()
            self._parameter_form = ParameterForm(parent=self.controlArea)
            
            self._parameter_form.addParameter(
                "delay",
                label="Delay for each sum iteration",
                value_for_type=0,
                value_change_callback=self._inputs_changed
            )

            self._parameter_form.addParameter(
                "list",
                label="List of elements to sum",
                value_for_type="",
                serialize=json.dumps,
                deserialize=json.loads,
                value_change_callback=self._inputs_changed
            )
            self._parameter_form.addStretch()
            self._update_parameter_values()

        def _inputs_changed(self):
            new_values = self._parameter_form.get_parameter_values()
            self.update_default_inputs(**new_values)

        def _update_parameter_values(self):
            initial_values = self.get_default_input_values()
            self._parameter_form.set_parameter_values(initial_values)

.. note:: 

    The full example can be found in `src/orangecontrib/ewokstest/sumlist_parameter_form.py`


There is a lot to unpack so let's do this step by step:

------

.. code:: python
    
    self._parameter_form = ParameterForm(parent=self.controlArea)

This line creates the ``ParameterForm`` in the ``controlArea`` of the widget. The ``controlArea`` (as opposed to the ``mainArea``) is the widget area where control elements (e.g. buttons) are located so it makes sense to put our form there.

------

.. code:: python

    self._parameter_form.addParameter(
        "delay",
        label="Delay for each sum iteration",
        value_for_type=0,
        value_change_callback=self._inputs_changed
    )

This part calls ``addParameter`` a first time to generate the first element of our form. 

``addParameter`` only has one mandatory argument: the name (``delay``) that is used to uniquely identify the parameter. 

The other specified arguments are:

* ``label``: A string that will be displayed next to the GUI element.
* ``value_for_type``: A Python value whose type will be used to determine the GUI element to show. In this case, we give a ``number`` (``0`` but it could be any number) so that ``ParameterForm`` shows a numerical spinbox. See the end of the page for a list of all possible values.
* ``value_change_callback``: The function that will be called when the value is changed. We will come back to this later.

------

.. code:: python

    self._parameter_form.addParameter(
        "list",
        label="List of elements to sum",
        value_for_type="",
        serialize=json.dumps,
        deserialize=json.loads,
        value_change_callback=self._inputs_changed
    )

This part calls ``addParameter`` a second time to generate the second element of our form used to specify the ``list`` parameter. 

We already saw the ``label`` and ``value_change_callback`` arguments. 

Since on the GUI side, a user can only input numbers or strings, this parameter will be a ``string`` (hence the ``string`` in ``value_for_type`` so that the GUI will have a textbox). 

However, we can apply a transformation to the value when retrieving it from the GUI: this is the role of the function given as ``deserialize`` argument. By doing ``json.loads`` on the string representing a ``list``, we can get a list as parameter value instead not a string. The ``serialize`` is the inverse operation (when setting the value from the widget to the GUI).

------

.. code:: python

    self._parameter_form.addStretch()

This line adds a blank area that will occupy any extra vertical space in the Orange widget.
This prevents the parameter widgets to expand vertically.

------

.. code:: python

    def _inputs_changed(self):
        new_values = self._parameter_form.get_parameter_values()
        self.update_default_inputs(**new_values)

This is the function that will be called when the ``ParameterForm`` values change. ``get_parameter_values`` allows us to retrieve the dictionnary of parameter values (the keys being the ``name`` specified in ``addParameter``).

For these values to be used as inputs of the Ewoks task, we must update the default inputs of the task. This is done by ``update_default_inputs`` that takes arguments ``key=value``, the keys being the names of the Ewoks task inputs. Since the names of the parameters and of the Ewoks task inputs are the same (``list`` and ``delay``), we can directly use the ``new_values`` dictionnary coming from the ``ParameterForm``.

.. warning::

    The parameter values are set as **default inputs**. It means they will be overwritten by **dynamic inputs** that come from upstream connections or by execution inputs. 

------

.. code:: python

    def _update_parameter_values(self):
        initial_values = self.get_default_input_values()
        self._parameter_form.set_parameter_values(initial_values)

A saved workflow can hold default values for each task. By calling this function when creating the Orange widget, we ensure that these initial default values are propagated to the parameter form so that it is initialized with the right values.


Possible `value_for_type` and their associated GUI elements
===========================================================

.. list-table::
   :header-rows: 1

   * - Type
     - `value_for_type` example
     - GUI element
     - Notes
   * - `bool`
     - `True`
     - Checkbox
     - 
   * - `Number`
     - `0`
     - Spinbox
     - The spinbox will allow decimals only if a `float` is supplied 
   * - `Sequence`
     - `['Choice1', 'Choice2', 'Choice3']`
     - Combobox
     - The choices of the combobox must be specified in the given sequence (an empty list will generate a combobox with no choices).
   * - `str`
     - `""`
     - Textbox
     - Can be used as input for list and dict if `json` is used for the serialization/deserialization.

.. note:: 

    In case the textbox is meant for a path (to a file/directory/HDF5 entity), the `select` argument can be supplied in conjunction of the string `value_for_type`. 
    
    Specifying the `select` argument will make a button appear next to the textbox that opens a file browser. Selecting an entity in this file browser will automatically fill the checkbox with the entity path. 
    
    The possible selectable entities depend on the value of the `select` argument:  `file`, `newfile`, `directory`, `h5dataset`, `h5group`, `files`, `newfiles`, `directories`, `h5datasets` or `h5groups`. 