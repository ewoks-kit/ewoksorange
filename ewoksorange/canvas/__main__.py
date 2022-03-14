"""Main entry point

    python -m ewoksorange.canvas --with_example

Which is equivalent to

    python -m Orange.canvas

but it registers the example Addon before launching.
"""

import sys
from .main import main

if __name__ == "__main__":
    sys.exit(main())
