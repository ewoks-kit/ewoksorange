import inspect
from Orange.widgets.settings import Setting


def is_setting(obj):
    return isinstance(obj, Setting)


def get_settings(widget_class):
    return dict(inspect.getmembers(widget_class, is_setting))
