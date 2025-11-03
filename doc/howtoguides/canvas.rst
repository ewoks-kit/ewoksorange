.. _How to launch Orange canvas ?:

How to launch Orange canvas ?
=============================

`Orange canvas <https://orange-canvas-core.readthedocs.io/en/latest/>`_ is a GUI allowing users to define and tune a workflow. It is used by several projects like `est <https://gitlab.esrf.fr/workflow/ewoksapps/est>`_, `ewoksfluo <https://gitlab.esrf.fr/workflow/ewoksapps/ewoksfluo>`_ or `ewoksndreg <https://gitlab.esrf.fr/workflow/ewoksapps/ewoksndreg>`_ 
There are several ways to launch this canvas:

* :ref:`launch_canvas_from_ewoks_canvas`
* :ref:`launch_canvas_from_orange_canvas`
* :ref:`launch_canvas_from_ewoks_execute`

.. _launch_canvas_from_ewoks_canvas:

1. using `ewoks-canvas` application (recommended)
"""""""""""""""""""""""""""""""""""""""""""""""""

.. tab-set::

    .. tab-item:: using 'ewoks' CLI

        .. code-block:: bash

            ewoks-canvas /path/to/orange_wf.ows

        .. note:: launching the canvas with examples available:

            .. code-block:: bash

                ewoks-canvas --with-examples

    .. tab-item:: using 'python3' CLI

        .. code-block:: bash

            python3 -m ewoksorange.gui.canvas /path/to/orange_wf.ows

.. _launch_canvas_from_orange_canvas:

2. using `orange-canvas` application
"""""""""""""""""""""""""""""""""""""""""""""""""

.. tab-set::

    .. tab-item:: using 'orange-canvas' CLI

        .. code-block:: bash

            orange-canvas /path/to/orange_wf.ows [--config ewoksorange.gui.canvas.config.Config]

    .. tab-item:: using 'python3' CLI

        .. code-block:: bash

            python3 -m orangecanvas /path/to/orange_wf.ows [--config ewoksorange.gui.canvas.config.Config]


.. _launch_canvas_from_ewoks_execute:

3. using `ewoks-execute` application
"""""""""""""""""""""""""""""""""""""""""""""""""

.. tab-set::

    .. tab-item:: using 'ewoks' CLI

        .. code-block:: bash

            ewoks execute /path/to/ewoks_wf.json --engine orange
            ewoks execute /path/to/orange_wf.ows --engine orange

    .. tab-item:: using 'python3' CLI

        .. code-block:: bash

            python3 -m ewoks execute /path/to/ewoks_wf.json --engine orange
            python3 -m ewoks execute /path/to/orange_wf.ows --engine orange
