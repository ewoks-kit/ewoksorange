
Getting started
===============

Install requirements

.. code-block:: bash

    pip install ewoksorange[orange]

.. warning::

    `ewoksorange` comes without any predefined Qt binding. 
    
    You will need to install one to use `ewoksorange`.
    Possible bindings are `PyQt5`, `PyQt6`, `PySide` and `PySide2`. 

    For example, to use `PyQt6`:

    .. code-block:: bash

        pip install PyQt6

.. admonition:: OASYS2 use case
    :class: dropdown

    When using OASYS2 instead of Orange3, install the requirements like this instead

    .. code-block:: bash

        pip install ewoksorange[oasys2]

    OASYS2 already depends on `PyQt6` so no Qt binding needs to be installed.

Launch the graphical interface

.. code-block:: bash

    ewoks-canvas
