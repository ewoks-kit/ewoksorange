import logging
import sys
from contextlib import contextmanager

from ...orange_version import ORANGE_VERSION

_logger = logging.getLogger(__file__)

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.canvas import conf as _oasys_conf_module
    from oasys.canvas.__main__ import main as _main

    from ..canvas.config import Config as _Config

    _oasys_conf_module.oasysconf = _Config

    def arg_parser():
        import argparse

        parser = argparse.ArgumentParser()

        parser.add_argument(
            "--no-discovery",
            action="store_true",
            help="Don't run widget discovery (use full cache instead)",
        )
        parser.add_argument(
            "--force-discovery",
            action="store_true",
            help="Force full widget discovery (invalidate cache)",
        )
        parser.add_argument(
            "--clear-widget-settings",
            action="store_true",
            help="Remove stored widget setting",
        )
        parser.add_argument(
            "--no-welcome", action="store_true", help="Don't show welcome dialog."
        )
        parser.add_argument(
            "--no-splash", action="store_true", help="Don't show splash screen."
        )
        parser.add_argument(
            "-l",
            "--log-level",
            help="Logging level (0, 1, 2, 3, 4)",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--no-redirect",
            action="store_true",
            help="Do not redirect stdout/err to canvas output view.",
        )
        parser.add_argument("--style", help="QStyle to use", type=str, default="Fusion")
        parser.add_argument(
            "--stylesheet",
            help="Application level CSS style sheet to use",
            type=str,
            default="orange.qss",
        )
        parser.add_argument(
            "--qt",
            help="Additional arguments for QApplication",
            type=str,
            default=None,
        )
        parser.add_argument(
            "--no-update",
            action="store_true",
            help="Stop automatic update internal libraries",
        )
        return parser

elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from Orange.canvas.__main__ import main as _main
    from orangecanvas.main import arg_parser
else:
    import orangecanvas.main
    from orangecanvas.application.canvasmain import (
        CanvasMainWindow as _CanvasMainWindow,
    )
    from orangecanvas.main import arg_parser

    from .schemeedit import SchemeEditWidget as _SchemeEditWidget

    if not hasattr(_CanvasMainWindow, "EDITOR_WIDGET_CONSTRUCTOR"):
        _logger.info(
            "Canvas main window does not have an editor widget constructor, skipping adding the 'trigger' action to links"
        )

    class Main(orangecanvas.main.Main):

        def create_main_window(self) -> _CanvasMainWindow:
            """Create the (initial) main window."""
            _CanvasMainWindow.EDITOR_WIDGET_CONSTRUCTOR = _SchemeEditWidget
            # Redefining the 'EDITOR_WIDGET_CONSTRUCTOR' allow use to add features to the default 'SchemeEditWidget' like adding actions to the link.
            return _CanvasMainWindow()

    def _main(argv=None):
        return Main().run(argv)


@contextmanager
def _temporary_log_handlers(log_level):
    logger = logging.getLogger("ewoksorange")
    logger.setLevel(log_level)
    if logger.hasHandlers():
        yield
    else:
        stdouthandler = logging.StreamHandler(sys.stdout)
        logger.addHandler(stdouthandler)
        yield
        logger.removeHandler(stdouthandler)


def main(argv=None):
    parser = arg_parser()

    parser.add_argument(
        "--with-examples",
        action="store_true",
        help="Register Orange add-on for 'ewoksorange' example Ewoks tasks.",
    )
    parser.add_argument(
        "--with-demo",
        action="store_true",
        help="Register Orange add-on for 'ewokscore' demo Ewoks tasks.",
    )

    if argv is None:
        argv = sys.argv
    options, _ = parser.parse_known_args(argv[1:])

    if "--with-examples" in argv:
        argv.pop(argv.index("--with-examples"))

    if "--with-demo" in argv:
        argv.pop(argv.index("--with-demo"))

    if "--force-discovery" not in argv:
        argv.append("--force-discovery")

    if ORANGE_VERSION != ORANGE_VERSION.oasys_fork:
        if "--config" not in argv:
            argv += ["--config", "ewoksorange.gui.canvas.config.Config"]

    with _temporary_log_handlers(options.log_level):
        if options.with_examples:
            from orangecontrib.ewokstest import enable_ewokstest_category

            enable_ewokstest_category()
        if options.with_demo:
            from orangecontrib.ewoksdemo import enable_ewoksdemo_category

            enable_ewoksdemo_category()

    _main(argv)
