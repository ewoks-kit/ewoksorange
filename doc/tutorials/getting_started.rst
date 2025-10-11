
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

.. admonition:: Oasys use case
    :class: dropdown

    When using Oasys instead of Orange3, install the requirements like this instead

    .. code-block::

        pip install oasys1
        pip install AnyQt
        pip install importlib_resources  # python_version < "3.9"
        pip install ewokscore
        pip install pytest
        pip install --no-deps ewoksorange

Launch the graphical interface

.. code-block:: bash

    ewoks-canvas
