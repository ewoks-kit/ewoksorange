"""Commonly used Orange3 components for implementing Orange Widgets."""

import warnings

from orangewidget.settings import Setting  # noqa F401

from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.widgets import gui  # noqa F401
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from Orange.widgets import gui  # noqa F401
else:
    from orangewidget import gui  # noqa F401

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    _Input = None
    _Output = None
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from orangewidget.widget import Input as _Input  # noqa F401
    from orangewidget.widget import Output as _Output  # noqa F401
else:
    from orangewidget.widget import Input as _Input  # noqa F401
    from orangewidget.widget import Output as _Output  # noqa F401

# OWBaseWidget: lowest level Orange widget base class
# OWWidget: highest level Orangewidget base class.
if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.widgets.widget import OWWidget  # noqa F401

    OWBaseWidget = OWWidget
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from Orange.widgets.widget import OWWidget  # noqa F401
    from orangewidget.widget import OWBaseWidget  # noqa F401
else:
    from orangewidget.widget import OWBaseWidget  # noqa F401

    OWWidget = OWBaseWidget


def __getattr__(name):
    if name == "Input":
        warnings.warn(
            f"Accessing '{name}' from '{__name__}' is deprecated and will be "
            "removed in a future release. Please import it from "
            "'ewoksorange.gui.orange_utils.signals' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _Input

    if name == "Output":
        warnings.warn(
            f"Accessing '{name}' from '{__name__}' is deprecated and will be "
            "removed in a future release. Please import it from "
            "'ewoksorange.gui.orange_utils.signals' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _Output

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
