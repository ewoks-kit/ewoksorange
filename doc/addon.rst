Orange3 add-on
==============

An Orange3 add-on project looks like this

.. code-block::

    .
    ├── orangecontrib  # Orange3 namespace package
    │   ├── __init__.py
    │   └── xrpd_pipelines
    │       ├── __init__.py
    │       ├── widget1.py
    │       ├── widget2.py
    │       ├── ...
    │       ├── icons
    │       └── tutorials
    ├── xrpd_pipelines  # core package of the project
    │   ├── __init__.py
    │   ...
    ├── docs  # sphinx documentation
    ├── README.md
    ├── setup.cfg
    └── setup.py

where *./orangecontrib* is declared as a namespace package

.. code-block:: python

    # ./orangecontrib/__init__.py

    __import__("pkg_resources").declare_namespace(__name__)

and we create a widget category

.. code-block:: python

    # ./orangecontrib/xrpd/__init__.py

    import sysconfig

    NAME = "XRPD"

    DESCRIPTION = "X-ray Powder Diffraction"

    LONG_DESCRIPTION = "X-ray Powder Diffraction"

    ICON = "icons/category.svg"

    BACKGROUND = "light-blue"

    WIDGET_HELP_PATH = (
        # Development documentation (make htmlhelp in ./doc)
        ("{DEVELOP_ROOT}/doc/_build/htmlhelp/index.html", None),
        # Documentation included in wheel
        ("{}/help/xrpd-pipelines/index.html".format(sysconfig.get_path("data")), None),
        # Online documentation url
        ("http://xrpd-pipelines.readthedocs.io/en/latest/", ""),
    )


To configure the project for installation you can explicitely add entry-points and
package-data to the configuration

.. code-block:: yaml

    [options.package_data]
    * = *.ows, *.png, *.svg

    [options.entry_points]
    orange3.addon =
        xrpd-pipelines=orangecontrib.xrpd_pipelines
    orange.widgets =
        XRPD=orangecontrib.xrpd_pipelines
    orangecanvas.examples =
        XRPD=orangecontrib.xrpd_pipelines.tutorials
    orange.widgets.tutorials =
        XRPD=orangecontrib.xrpd_pipelines.tutorials
    orange.canvas.help =
        html-index=orangecontrib.xrpd_pipelines:WIDGET_HELP_PATH

Note that _XRPD_ must equal to the category name `orangecontrib.xrpd.NAME`.

Tutorials must be set in both `orangecanvas.examples` and `orange.widgets.tutorials` to be able
to be discovered whatever the Orange installation.

Alternatively tutorials and widgets can the discovered automatically but this requires installing
all dependencies *before* installing the project

.. code-block:: python

    from ewoksorange.setuptools import setup

    if __name__ == "__main__":
        setup(__file__, name="xrpd-pipelines")
