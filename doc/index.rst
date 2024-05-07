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

Launch the graphical interface

.. code:: bash

    ewoks-canvas

Run the tests

.. code:: bash

    pip install ewoksorange[test]
    pytest --pyargs ewoksorange.tests

Implement Orange Widgets
------------------------

`Orange <https://orangedatamining.com/>`_ widgets associated to the Ewoks tasks provided by an Ewoks project.

For this, the Ewoks project needs to be setup as an *Orange Add-on* project. 
A template project can be found `here <https://gitlab.esrf.fr/workflow/ewoksapps/ewoksorangetemplate/>`_.

Further documentation can be found `here <https://ewoksorangetemplate.readthedocs.io/>`_.

Documentation
-------------

.. toctree::
    :maxdepth: 2

    canvas
    note_on_designs
    API
