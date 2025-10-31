"""Commonly used Orange3 components for implementing Orange Widgets."""

from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from orangewidget.settings import Setting  # noqa F401

    Input = None
    Output = None
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from orangewidget.settings import Setting  # noqa F401
    from orangewidget.widget import Input  # noqa F401
    from orangewidget.widget import Output  # noqa F401
else:
    from orangewidget.settings import Setting  # noqa F401
    from orangewidget.widget import Input  # noqa F401
    from orangewidget.widget import Output  # noqa F401
