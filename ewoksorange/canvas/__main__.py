"""Main entry point

    python -m ewoksorange.canvas

Which is equivalent too

    python -m Orange.canvas

Exists in case we need to register things before launching the canvas
"""


import sys
from Orange.canvas.__main__ import main as _main


def main(**kw):
    # Register an addon library with wasn't registered at runtime.
    # import orange3unregistered
    # from ewoksorange.registration import register_addon_package
    # register_addon_package(orange3unregistered, distroname="ewoks_example_addon")
    _main(**kw)


if __name__ == "__main__":
    sys.exit(main())
