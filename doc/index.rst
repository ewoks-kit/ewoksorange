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

Implement Orange Widgets
------------------------

An Ewoks project that implements `Orange <https://orangedatamining.com/>`_ widgets associated to the Ewoks tasks it provides, needs
to be setup as an *Orange Add-on* project. A template project can be found `here <https://gitlab.esrf.fr/workflow/ewoksapps/ewoksorangetemplate/>`_.
Further documentation can be found `here <https://ewoksorangetemplate.readthedocs.io/>`_.

Documentation
-------------

.. toctree::
    :maxdepth: 2

    canvas
    note_on_designs
    API
