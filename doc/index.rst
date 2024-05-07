===========
ewoksorange
===========

*ewoksorange* provides a desktop graphical interface for `ewoks <https://ewoks.readthedocs.io/>`_.

*ewoksorange* is developed by the `Software group <http://www.esrf.eu/Instrumentation/software>`_ of the `European Synchrotron <https://www.esrf.eu/>`_.

Getting started
---------------

Install requirements

.. code:: bash

    pip install ewoksorange[orange]

.. note::
    
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






Documentation
-------------

.. toctree::
    :maxdepth: 2

    canvas
    writing_orange_widgets
    API
