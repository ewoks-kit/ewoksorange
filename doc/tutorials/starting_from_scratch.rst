.. _Starting a new project from scratch:

Starting a New Project from Scratch
===================================

`Orange <https://orangedatamining.com/>`_ widgets can be written and linked to Ewoks
tasks defined within an Ewoks project.

To enable this, the Ewoks project must be set up as an *Orange add-on*.
You can easily bootstrap such a project using the 
`Ewoks cookiecutter template <https://gitlab.esrf.fr/workflow/ewoksapps/ewokscookie>`_.

A minimal working example is available 
`here <https://gitlab.esrf.fr/workflow/ewoksapps/ewoks-orange-example-addon>`_ and
is described below.

Python Distribution Layout
--------------------------

An Orange add-on project for Ewoks typically contains **two Python packages**:

- **Main package** – Implements Ewoks tasks and *Qt* components
  (e.g. ``ewoks_orange_example_addon``).
- **Namespace package** – Provides Orange *Qt* widgets
  (under ``orangecontrib``, usually with the same subpackage name).

When using a `src-layout <https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/>`_, 
the project structure typically looks like this:

.. code-block:: bash

    .
    ├── pyproject.toml
    ├── README.md
    ├── CHANGELOG.md
    ├── CONTRIBUTING.md
    ├── LICENSE.md
    ├── doc
    │   └── ...
    └── src
        ├── ewoks_orange_example_addon
        │   ├── __init__.py
        │   ├── tasks
        │   │   ├── __init__.py
        │   │   └── exampletask.py
        │   └── tests
        │       ├── __init__.py
        │       ├── conftest.py
        │       └── test_exampletask.py
        └── orangecontrib
            └── ewoks_orange_example_addon
                ├── __init__.py
                └── exampletask.py

Orange Add-on Metadata
----------------------

The primary dependencies of an Ewoks-Orange project are:

- ``ewokscore`` (core Ewoks functionality)
- ``ewoksorange`` (Ewoks-Orange integration)

Example ``pyproject.toml``:

.. code-block:: toml

    dependencies = [
        "ewokscore",
        "ewoksorange",
    ]

Orange Metadata for GUI Display
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The add-on metadata displayed in the Orange Canvas GUI is defined in:

.. code-block:: python

    # src/orangecontrib/ewoks_orange_example_addon/__init__.py

    NAME = "Ewoks Orange Demo"
    DESCRIPTION = "An Ewoks project"

The ``NAME`` value determines how the add-on appears in the Orange widget panel.

Entry Points for Orange Discovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Orange uses entry points to auto-discover add-ons and their widgets:

.. code-block:: toml

    [project.entry-points."orange3.addon"]
    "ewoks_orange_example_addon" = "orangecontrib.ewoks_orange_example_addon"

    [project.entry-points."orange.widgets"]
    "Examples" = "orangecontrib.ewoks_orange_example_addon"

Optional: Ewoks Task Discovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can optionally declare Ewoks task entry points for auto-discovery:

.. code-block:: toml

    [project.entry-points."ewoks.tasks.class"]
    "ewoks_orange_example_addon.tasks.*" = "ewoks_orange_example_addon"

Optional: Distribution Metadata for PyPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To make the project discoverable on PyPI, include:

.. code-block:: toml

    [project]
    name = "ewoks-orange-example-addon"
    version = "0.0.1-alpha"
    keywords = [
        "orange3 add-on",
        "ewoks"
    ]

Defining an Ewoks Task
----------------------

An Ewoks task is a standard computational unit without any *Qt* or interactive components.

Example:

.. code-block:: python

    # src/ewoks_orange_example_addon/tasks/exampletask.py

    from ewokscore import Task

    class ExampleTask(Task, input_names=["number"], output_names=["result"]):
        """Add +1 to a number"""

        def run(self):
            self.outputs.result = self.inputs.number + 1

Creating an Ewoks-Orange Widget
-------------------------------

An Ewoks-Orange widget provides the *Qt* user interface for the corresponding Ewoks task.
It typically includes:

- Widgets for user-defined Ewoks task inputs
- Widgets for displaying results

A typical widget implements the following interactions:

- **Load File → Initialize Display:**  
  Populate widgets with saved Ewoks inputs.
- **User Input → Store:**  
  Store user-defined inputs at runtime.
- **Upstream Outputs → Update Inputs:**  
  Receive inputs from upstream workflow nodes.
- **Execution → Update Display:**  
  Display the Ewoks task outputs after execution.

To create a widget, subclass one of the Ewoks-Orange base widget classes, such as
``OWEwoksWidgetOneThread`` — which executes the task in a separate thread to keep the GUI responsive.

Use the ``ewokstaskclass`` argument to link the widget to its Ewoks task, and define the ``name`` 
attribute for the widget panel display.

Example:

.. code-block:: python

    from AnyQt import QtWidgets
    from ewoksorange.bindings import OWEwoksWidgetOneThread
    from ewoks_orange_example_addon.tasks.exampletask import ExampleTask

    __all__ = ["OWExampleTask"]

    class OWExampleTask(OWEwoksWidgetOneThread, ewokstaskclass=ExampleTask):
        """Orange widget that delegates computation to an Ewoks task.

        This class manages two types of inputs:

        - Default inputs: user inputs saved in the workflow file
        - Dynamic inputs: values received from upstream nodes (not saved)

        The class implements Qt widgets for displaying task inputs and outputs.
        """

        name = "Demo"
        description = "Add +1 to a number"

        def __init__(self) -> None:
            super().__init__()
            self._init_control_area()
            self._init_main_area()

        def _init_control_area(self) -> None:
            """Create widgets for user inputs."""
            super()._init_control_area()
            layout = self._get_control_layout()

            label = QtWidgets.QLabel("Number")
            self._widgetNumber_value = QtWidgets.QSpinBox()
            self._widgetNumber_value.editingFinished.connect(self._default_inputs_changed)
            layout.addWidget(label)
            layout.addWidget(self._widgetNumber_value)
            layout.addStretch()

        def _init_main_area(self) -> None:
            """Create widgets for task outputs."""
            super()._init_main_area()
            layout = self._get_main_layout()

            label = QtWidgets.QLabel("Result")
            self._widgetResult_value = QtWidgets.QLineEdit()
            self._widgetResult_value.setReadOnly(True)
            layout.addWidget(label)
            layout.addWidget(self._widgetResult_value)
            layout.addStretch()

        def _initialize_widgets(self) -> None:
            """Initialize widgets with saved workflow inputs."""
            number = self.get_default_input_value("number", None)
            if number is not None:
                self._widgetNumber_value.setValue(number)

        def _default_inputs_changed(self) -> None:
            """Handle user input changes."""
            self.update_default_inputs(number=self._widgetNumber_value.value())

        def handleNewSignals(self) -> None:
            """Handle upstream outputs."""
            number = self.get_dynamic_input_value("number", None)
            if number is not None:
                self._widgetNumber_value.setValue(number)
                self._widgetNumber_value.setReadOnly(True)
            else:
                self._widgetNumber_value.setReadOnly(False)
            super().handleNewSignals()

        def task_output_changed(self) -> None:
            """Display Ewoks task outputs."""
            result = self.get_task_output_value("result", None)
            if result is not None:
                self._widgetResult_value.setText(str(result))
            super().task_output_changed()

.. note::

    ``super()._init_control_area`` adds two execution buttons:
    
    - **Execute:** runs only the current node (``execute_ewoks_task_without_propagation``)
    - **Trigger:** runs the current node and all downstream nodes (``execute_ewoks_task``)

Ewoks-Orange Execution Call Stack
---------------------------------

When the user executes an Ewoks-Orange widget from the canvas, the following sequence occurs:

.. mermaid::

    sequenceDiagram
        participant User
        participant Widget
        participant Task as Ewoks Task
        participant Channel as Output Channel(s)
        participant SignalManager
        participant DownstreamWidget as Downstream Widget(s)

        User->>Widget: Click "Trigger"
        Widget->>Task: execute_ewoks_task()
        Task->>Widget: propagate_downstream()

        loop For each output channel
            Widget->>Channel: send()
            Channel->>SignalManager: send()
        end

        Task->>Widget: 🔧 task_output_changed() 🔧

        loop For each connected output channel
            SignalManager->>DownstreamWidget: set_dynamic_input(output_name, value)
        end

        SignalManager->>DownstreamWidget: 🔧 handleNewSignals() 🔧
        Note over SignalManager,DownstreamWidget: One handleNewSignals() call per downstream widget
        Note over Widget,Task: Concurrent Task Execution

🔧 : to be implemented like in the ``OWExampleTask`` widget above.
