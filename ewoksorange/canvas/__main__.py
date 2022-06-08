"""Main entry point

.. code: bash

    ewoks-canvas --with-examples

Which is equivalent to

.. code: bash

    python -m orangecanvas --config orangewidget.workflow.config.Config

or

.. code: bash

    python -m Orange.canvas

or

.. code: bash

    orange-canvas

but it registers the example add-on before launching.
"""

import sys
from .main import main

if __name__ == "__main__":
    sys.exit(main())
