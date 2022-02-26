Examples
========

Launch the Orange canvas and load an Orange3 or Ewoks workflow with the ewoks CLI

.. code-block:: bash

    ewoks execute /path/to/ewoks_wf.json --binding orange
    ewoks execute /path/to/orange_wf.ows --binding orange

Launch the Orange canvas with the examples Addon

.. code-block:: bash

    python -m ewoksorange.canvas --with_example

or alternatively install the example Addon

.. code-block:: bash

    python -m pip install ewoksorange/tests/examples/ewoks_example_1_addon
    python -m pip install ewoksorange/tests/examples/ewoks_example_2_addon

and launch the Orange canvas normally

.. code-block:: bash

    python -m orangecanvas

or when Orange3 is installed

.. code-block:: bash

    python -m Orange.canvas
