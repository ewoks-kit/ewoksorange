.. _How to launch Orange canvas ?:

How to launch Orange canvas ?
=============================

`Orange canvas <https://orange-canvas-core.readthedocs.io/en/latest/>`_ is a GUI allowing users to define and tune a workflow. It is used by several projects like `est <https://gitlab.esrf.fr/workflow/ewoksapps/est>`_, `ewoksfluo <https://gitlab.esrf.fr/workflow/ewoksapps/ewoksfluo>`_ or `ewoksndreg <https://gitlab.esrf.fr/workflow/ewoksapps/ewoksndreg>`_ 
There are several ways to launch this canvas.

.. tab-set::

    .. tab-item:: 'ewoks-canvas'

        .. tab-set::

            .. tab-item:: 'ewoks' CLI

                .. code-block:: bash

                    ewoks-canvas /path/to/orange_wf.ows

                .. note:: launch with examples:

                    .. code-block:: bash

                        ewoks-canvas --with-examples

            .. tab-item:: 'python3' CLI

                .. code-block:: bash

                    python3 -m ewoksorange.canvas /path/to/orange_wf.ows

    .. tab-item:: 'orange-canvas'

        .. tab-set::

            .. tab-item:: 'orange-canvas' CLI

                .. code-block:: bash

                    orange-canvas /path/to/orange_wf.ows [--config ewoksorange.canvas.config.Config]

            .. tab-item:: 'python3' CLI

                .. code-block:: bash

                    python3 -m orangecanvas /path/to/orange_wf.ows [--config ewoksorange.canvas.config.Config]

    .. tab-item:: 'ewoks-execute'

        .. tab-set::

            .. tab-item:: 'ewoks execute' CLI

                .. code-block:: bash

                    ewoks execute /path/to/ewoks_wf.json --engine orange
                    ewoks execute /path/to/orange_wf.ows --engine orange

            .. tab-item:: 'python3' CLI

                .. code-block:: bash

                    python3 -m ewoks execute /path/to/ewoks_wf.json --engine orange
                    python3 -m ewoks execute /path/to/orange_wf.ows --engine orange
