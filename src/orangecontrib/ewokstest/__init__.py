import sysconfig

NAME = "Ewoks Test"

DESCRIPTION = "Short Test"

LONG_DESCRIPTION = "Long Test"

ICON = "icons/category.svg"

BACKGROUND = "light-blue"

WIDGET_HELP_PATH = (
    # Development documentation (make htmlhelp in ./doc)
    ("{DEVELOP_ROOT}/doc/_build/htmlhelp/index.html", None),
    # Documentation included in wheel
    ("{}/help/orange3-example/index.html".format(sysconfig.get_path("data")), None),
    # Online documentation url
    ("http://orange3-example-addon.readthedocs.io/en/latest/", ""),
)


def widget_discovery(discovery):
    """Do not show any widgets"""
    pass


def enable_ewokstest_category():
    global widget_discovery
    try:
        del widget_discovery
    except NameError:
        pass


def is_ewokstest_category_enabled() -> bool:
    try:
        widget_discovery(None)
    except NameError:
        return True
    return False
