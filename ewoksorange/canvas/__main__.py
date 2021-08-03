"""Main entry point

    python -m ewoksorange.canvas --with_example

Which is equivalent to

    python -m Orange.canvas

but it registers the example Addon before launching.
"""


import sys
from Orange.canvas.__main__ import main as _main


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        argv.pop(argv.index("--with_example"))
    except ValueError:
        with_example = False
    else:
        with_example = True

    if with_example:
        from ewoksorange.registration import register_addon_package
        from ewoksorange.tests.examples import ewoks_example_1_addon
        from ewoksorange.tests.examples import ewoks_example_2_addon

        register_addon_package(ewoks_example_1_addon)
        register_addon_package(ewoks_example_2_addon)

    _main(argv)


if __name__ == "__main__":
    sys.exit(main())
