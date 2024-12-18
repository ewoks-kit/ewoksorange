.. _Starting a new project from scratch:

Starting a new project from scratch
===================================

`Orange <https://orangedatamining.com/>`_ widgets can be written and associated to the Ewoks tasks provided by an Ewoks project.

For this, the Ewoks project needs to be setup as an *Orange Add-on* project. To bootstrap your project you can use `The ewoks cookie cutter project <https://gitlab.esrf.fr/workflow/ewoksapps/ewokscookie>`_

Example: adding a new section to the `ewoksorange` `orangecontrib` module
-------------------------------------------------------------------------

If you want to simply include a new EwoksWidget to an existing orangecontrib project you will need the following:

* add a new module (named 'testtuto' here) with the file containing the widget (folder + '__init__.py' file to `orangecontrib`)

    src/orangecontrib/testtuto/
    ├── __init__.py
    └── ClipDataOW.py


* Update the setup.cfg file: update 'orange3.addon' and 'orange.widgets':

    .. code-block:: text

        orange3.addon =
            ewoksdemo=orangecontrib.ewoksdemo
            ewoksnowidget=orangecontrib.ewoksnowidget
        +    testtuto=orangecontrib.testtuto
        orange.widgets =
            Ewoks Demo=orangecontrib.ewoksdemo
            Ewoks Without Widgets=orangecontrib.ewoksnowidget
            Ewoks Test=orangecontrib.ewokstest
        +    Test Tuto=orangecontrib.testtuto
