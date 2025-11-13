"""
Metaclass and class preparation utilities for owwidgets package.
"""

import inspect
from typing import Any

from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from orangewidget.settings import Setting
    from orangewidget.widget import WidgetMetaClass
else:
    from orangewidget.settings import Setting

    if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        from Orange.widgets.widget import WidgetMetaClass
    else:
        from orangewidget.widget import OWBaseWidget

        WidgetMetaClass = type(OWBaseWidget)

from ..orange_utils import _signals


class OWEwoksWidgetMetaClass(WidgetMetaClass):
    """
    Metaclass used to prepare widget classes with Ewoks bindings.
    """

    def __new__(metacls, name, bases, attrs, ewokstaskclass=None, **kw):
        """
        Create a new widget class; if `ewokstaskclass` is provided prepare the class.

        :param name: New class name.
        :param bases: Base classes.
        :param attrs: Attribute dict for the class.
        :param ewokstaskclass: Optional Ewoks Task class to attach.
        :return: Newly created class type.
        """
        if ewokstaskclass:
            _prepare_OWEwoksWidgetclass(attrs, ewokstaskclass)
        return super().__new__(metacls, name, bases, attrs, **kw)


# Ensure compatibility between old orange widget and new
# orangewidget.widget.WidgetMetaClass. This was before the split of the two
# projects. Parameter name "openclass" is undefined in the old version.
ow_build_opts = dict()
if "openclass" in inspect.signature(WidgetMetaClass).parameters:
    ow_build_opts["openclass"] = True


def _prepare_OWEwoksWidgetclass(namespace: dict, ewokstaskclass: Any) -> None:
    """
    Attach Ewoks task class and default settings to a widget class namespace.
    This needs to be called before signal and setting parsing.

    :param namespace: Class attribute dictionary to modify.
    :param ewokstaskclass: The Ewoks Task class to attach (used for input/output introspection).
    """

    # Add the Ewoks class as an attribute to the Orange widget class
    namespace["ewokstaskclass"] = ewokstaskclass

    # Make sure the values above are always the default setting values:
    # https://orange3.readthedocs.io/projects/orange-development/en/latest/tutorial-settings.html
    # schema_only=False: when a widget is removed, its settings are stored to be used
    #                    as defaults for future instances of this widget.
    # schema_only=True: setting defaults should not change. Future instances of this widget
    #                   have the default settings hard-coded in this function.
    schema_only = True

    # Add the settings as widget class attributes
    namespace["_ewoks_default_inputs"] = Setting(dict(), schema_only=schema_only)
    namespace["_ewoks_varinfo"] = Setting(dict(), schema_only=schema_only)
    namespace["_ewoks_execinfo"] = Setting(dict(), schema_only=schema_only)
    namespace["_ewoks_task_options"] = Setting(dict(), schema_only=schema_only)

    # Deprecated:
    namespace["default_inputs"] = Setting(dict(), schema_only=schema_only)

    # Add missing inputs and outputs as widget class attributes
    _signals.validate_signals(
        namespace,
        "inputs",
        name_to_ignore=namespace.get("_ewoks_inputs_to_hide_from_orange", tuple()),
    )
    _signals.validate_signals(
        namespace,
        "outputs",
        name_to_ignore=namespace.get("_ewoks_outputs_to_hide_from_orange", tuple()),
    )
