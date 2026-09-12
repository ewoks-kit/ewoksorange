import argparse
import os
import sys
import tempfile
from functools import partial
from typing import List
from typing import Optional
from typing import Union

import h5py
import numpy
import silx.io
from silx.gui import qt
from silx.gui.hdf5 import Hdf5ContextMenuEvent

from .model.links import LinkAwareTreeModel
from .model.live import LiveFileTreeModel
from .model.owned import OwnedFileLinksTreeModel
from .model.owned import OwnedFileTreeModel
from .model.static import StaticFileTreeModel
from .tree_viewer import Hdf5TreeViewer
from .viewer import Hdf5Viewer

ACCESS_MODELS = {
    "static": StaticFileTreeModel,
    "live": LiveFileTreeModel,
    "owned": OwnedFileTreeModel,
    "owned-links": OwnedFileLinksTreeModel,
    "owned-write": partial(OwnedFileLinksTreeModel, mode="a"),
    "links": LinkAwareTreeModel,
}
"""The tree model to use for each `--access` value."""

_ACCESS_HELP = {
    "static": "nobody writes it",
    "live": "another process may write it",
    "owned": "this process writes it",
    "owned-links": "this process writes it, and it has external links",
    "owned-write": "this process will write it later",
    "links": "its external links need their own options",
}


def create_argument_parser() -> argparse.ArgumentParser:
    """Return the parser of the command line."""
    parser = argparse.ArgumentParser(
        prog="python -m ewoksorange.gui.widgets.hdf5",
        description="Browse files supported by silx.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("files", nargs="*", help="files to open")
    parser.add_argument(
        "--tree-only",
        action="store_true",
        help="show the file tree without the data panel",
    )
    parser.add_argument(
        "--access",
        choices=list(ACCESS_MODELS),
        default="static",
        metavar="ACCESS",
        help="the regime of the files, which decides how they are opened\n"
        "(default: %(default)s)\n" + _accessHelp(),
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="open a generated file with one NXdata plot type per NXentry,\n"
        "and add a group and a dataset action to the tree context menu",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Show a viewer for the files given on the command line."""
    if argv is None:
        argv = sys.argv[1:]

    args = create_argument_parser().parse_args(argv)

    files = list(args.files)
    if args.demo:
        files.insert(0, _createDemoFile())

    app = qt.QApplication.instance() or qt.QApplication([])
    model = ACCESS_MODELS[args.access]()
    viewer: Union[Hdf5Viewer, Hdf5TreeViewer]
    if args.tree_only:
        viewer = Hdf5TreeViewer(model, toolbar=True)
        viewer.setWindowTitle(f"Ewoks HDF5 tree ({args.access})")
        viewer.resize(500, 600)
    else:
        viewer = Hdf5Viewer(model)
        viewer.setWindowTitle(f"Ewoks HDF5 viewer ({args.access})")
        viewer.resize(1000, 600)
    if args.demo:
        tree = viewer if args.tree_only else viewer.treeViewer
        tree.addContextMenuCallback(_addDemoActions)

    for filename in files:
        viewer.updateFile(filename)
    viewer.setVisible(True)
    return app.exec()


def _accessHelp() -> str:
    """Return one line per `--access` value, naming the model it uses."""
    width = max(len(name) for name in ACCESS_MODELS)
    lines = []
    for name, model in ACCESS_MODELS.items():
        if isinstance(model, partial):
            arguments = ", ".join(f"{k}={v!r}" for k, v in model.keywords.items())
            modelName = f"{model.func.__name__}({arguments})"
        else:
            modelName = model.__name__
        lines.append(f"{name:<{width}}  {modelName}")
        lines.append(f"{'':<{width}}  {_ACCESS_HELP[name]}")
    return "\n".join(lines)


def _addDemoActions(event: Hdf5ContextMenuEvent) -> None:
    """Add a group and a dataset action to the context menu of the tree."""
    menu = event.menu()
    if not menu.isEmpty():
        menu.addSeparator()

    for node in event.source().selectedH5Nodes(ignoreBrokenLinks=False):
        h5 = node.h5py_object
        if silx.io.is_group(h5):
            text = f"Count children of {node.basename}"
            message = f"{node.name} has {len(h5)} children"
        elif silx.io.is_dataset(h5):
            text = f"Describe {node.basename}"
            message = f"{node.name} has shape {h5.shape} and type {h5.dtype}"
        else:
            continue

        action = qt.QAction(text, event.source())
        action.triggered.connect(
            lambda checked=False, message=message: qt.QMessageBox.information(
                event.source(), "Demo action", message
            )
        )
        menu.addAction(action)


def _createDemoFile() -> str:
    """Create a file with one NXdata plot type per NXentry."""
    x = numpy.linspace(-5, 5, 64)
    image = numpy.sinc(numpy.hypot(*numpy.meshgrid(x, x)))
    angle = numpy.linspace(0, 8 * numpy.pi, 256)
    plots = {
        "curve": (numpy.sinc(x), ["x"], {"x": x}),
        "image": (image, ["y", "x"], {"x": x, "y": x}),
        "stack": (
            image * numpy.arange(1, 6)[:, None, None],
            [".", "y", "x"],
            {"x": x, "y": x},
        ),
        "scatter": (
            angle,
            ["px", "py"],
            {"px": angle * numpy.cos(angle), "py": angle * numpy.sin(angle)},
        ),
    }

    filename = os.path.join(tempfile.gettempdir(), "ewoksorange_demo.h5")
    with h5py.File(filename, "w") as h5file:
        h5file.attrs["NX_class"] = "NXroot"
        h5file.attrs["default"] = "curve"
        for name, (signal, axes, arrays) in plots.items():
            entry = h5file.create_group(name)
            entry.attrs["NX_class"] = "NXentry"
            entry.attrs["default"] = "data"
            data = entry.create_group("data")
            data.attrs["NX_class"] = "NXdata"
            data.attrs["signal"] = "signal"
            data.attrs["axes"] = axes
            data["signal"] = signal
            for axis, values in arrays.items():
                data[axis] = values
    return filename


if __name__ == "__main__":
    sys.exit(main())
