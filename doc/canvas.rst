Orange canvas
=============

Launch the Orange canvas

.. code-block:: bash

    ewoks-canvas /path/to/orange_wf.ows

or equivalently

.. code-block:: bash

    python3 -m ewoksorange.canvas /path/to/orange_wf.ows

When Orange3 is installed you can also launch the native Orange CLI

.. code-block:: bash

    orange-canvas /path/to/orange_wf.ows [--config ewoksorange.canvas.config.Config]

or equivalently

.. code-block:: bash

    python3 -m orangecanvas /path/to/orange_wf.ows [--config ewoksorange.canvas.config.Config]

Launch the Orange canvas using the Ewoks CLI

.. code-block:: bash

    ewoks execute /path/to/ewoks_wf.json --engine orange
    ewoks execute /path/to/orange_wf.ows --engine orange

or equivalently

.. code-block:: bash

    python3 -m ewoks execute /path/to/ewoks_wf.json --engine orange
    python3 -m ewoks execute /path/to/orange_wf.ows --engine orange

Launch the Orange canvas with the examples add-on

.. code-block:: bash

    ewoks-canvas --with-examples
