Orange canvas
=============

Launch the Orange canvas

.. code-block:: bash

    ewoks-canvas /path/to/orange_wf.ows

or for an installation with the system python

.. code-block:: bash

    python3 -m ewoksorange.canvas /path/to/orange_wf.ows

or when Orange3 is installed

.. code-block:: bash

    orange-canvas /path/to/orange_wf.ows

or for an installation with the system python

.. code-block:: bash

    python3 -m orangecanvas /path/to/orange_wf.ows

or for an installation with the system python

Launch the Orange canvas using the Ewoks CLI

.. code-block:: bash

    ewoks execute /path/to/ewoks_wf.json --engine orange
    ewoks execute /path/to/orange_wf.ows --engine orange

or for an installation with the system python

.. code-block:: bash

    python3 -m ewoks execute /path/to/ewoks_wf.json --engine orange
    python3 -m ewoks execute /path/to/orange_wf.ows --engine orange

Launch the Orange canvas with the examples add-on

.. code-block:: bash

    ewoks-canvas --with-examples

or alternatively install the example add-ons

.. code-block:: bash

    python3 -m pip install ewoksorange/tests/examples/ewoks_example_1_addon
    python3 -m pip install ewoksorange/tests/examples/ewoks_example_2_addon

and launch the Orange canvas with

.. code-block:: bash

    python3 -m orangecanvas

or when Orange3 is installed

.. code-block:: bash

    orange-canvas
