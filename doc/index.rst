===========
ewoksorange
===========

*ewoksorange* provides a desktop graphical interface for `ewoks <https://ewoks.readthedocs.io/>`_ based on `biolab <https://github.com/biolab>`_ the `orange-canvas-core <https://github.com/biolab/orange-canvas-core>`_ and the `orange-base-widget <https://github.com/biolab/orange-widget-base>`_.

*ewoksorange* is developed by the `Software group <http://www.esrf.eu/Instrumentation/software>`_ of the `European Synchrotron <https://www.esrf.eu/>`_.

Getting started
---------------

Install requirements

.. code:: bash

    pip install ewoksorange[orange]

.. warning::

    ewoksorange comes without any predefined Qt binding. So if you have none installed you will need one.
    For example if you want to add pyqt5 to your environment you can use:

    .. code:: bash

        pip install pyqt5

.. admonition:: Oasys use case
    :class: dropdown

    When using Oasys instead of Orange3, install the requirements like this instead

    .. code::

        pip install oasys1
        pip install AnyQt
        pip install importlib_resources  # python_version < "3.9"
        pip install ewokscore
        pip install pytest
        pip install --no-deps ewoksorange


Launch the graphical interface

.. code:: bash

    ewoks-canvas


.. toctree::
    :maxdepth: 2
    :hidden:

    how_to_guides/index
    tutorials/index
    development/index
    API
