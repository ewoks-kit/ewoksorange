Orange canvas
=============

Launch the Orange canvas

.. code-block:: bash

    python -m orangecanvas /path/to/orange_wf.ows

or when Orange3 is installed

.. code-block:: bash

    python -m Orange.canvas /path/to/orange_wf.ows

Launch the Orange canvas using the Ewoks CLI

.. code-block:: bash

    ewoks execute /path/to/ewoks_wf.json --binding orange
    ewoks execute /path/to/orange_wf.ows --binding orange

Launch the Orange canvas with the examples add-on

.. code-block:: bash

    python -m ewoksorange.canvas --with-examples

or alternatively install the example add-ons

.. code-block:: bash

    python -m pip install ewoksorange/tests/examples/ewoks_example_1_addon
    python -m pip install ewoksorange/tests/examples/ewoks_example_2_addon

and launch the Orange canvas normally

.. code-block:: bash

    python -m orangecanvas

or when Orange3 is installed

.. code-block:: bash

    python -m Orange.canvas
