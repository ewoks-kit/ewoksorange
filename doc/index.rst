.. |ewoksimg| image:: img/ewoksorange.png
    :scale: 100 %


========================
|ewoksimg|   ewoksorange
========================

*ewoksorange* provides desktop graphical interface for `ewoks <https://ewoks.readthedocs.io/>`_.

*ewoksorange* has been developed by the `Software group <http://www.esrf.eu/Instrumentation/software>`_ of the `European Synchrotron <https://www.esrf.eu/>`_.

Getting started
---------------

Install requirements

.. code:: bash

    pip install ewoksorange[orange]

Launch to graphical interface

.. code:: bash

    ewoks-canvas

Run the tests

.. code:: bash

    pip install ewoksorange[test]
    pytest --pyargs ewoksorange.tests

Documentation
-------------

.. toctree::
    :maxdepth: 2

    canvas
    addon
    note_on_designs
    API
