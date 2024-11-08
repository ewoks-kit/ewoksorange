Building the documentation
==========================

ewoksorange uses sphinx to generate the documentation. To build the documentation make sure the 'doc' extra-requirements are installed.

.. code-block:: bash

    pip install ewoksorange[doc]


Then you should be able to generate the documentation:

.. code-block:: bash

    sphinx-build doc [output_dir]
