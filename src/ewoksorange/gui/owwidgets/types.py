from .base import OWBaseWidget
from .base import OWEwoksBaseWidget


def is_orange_widget_class(widget_class) -> bool:
    """
    Return True if `widget_class` is an native Orange or Ewoks-Orange widget class.
    """
    return isinstance(widget_class, type) and issubclass(widget_class, OWBaseWidget)


def is_ewoks_widget_class(widget_class) -> bool:
    """
    Return True if `widget_class` is an Ewoks-Orange widget class.
    """
    return isinstance(widget_class, type) and issubclass(
        widget_class, OWEwoksBaseWidget
    )


def is_native_widget_class(widget_class) -> bool:
    """
    Return True if `widget_class` is a native Orange widget class.
    """
    return is_orange_widget_class(widget_class) and not is_ewoks_widget_class(
        widget_class
    )


def is_orange_widget(widget) -> bool:
    """
    Return True if `widget` is an Orange or Ewoks-Orange widget.
    """
    return isinstance(widget, OWBaseWidget)


def is_ewoks_widget(widget) -> bool:
    """
    Return True if `widget` is an Ewoks-Orange widget.
    """
    return isinstance(widget, OWEwoksBaseWidget)


def is_native_widget(widget) -> bool:
    """
    Return True if `widget` is a native Orange widget.
    """
    return is_orange_widget(widget) and not is_ewoks_widget(widget)
