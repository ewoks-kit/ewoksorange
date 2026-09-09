import h5py
import pytest
import silx.io.nxdata
from silx.gui import qt
from silx.gui.data.DataViewerFrame import DataViewerFrame

from ....gui.widgets.hdf5 import __main__ as main_module
from ....gui.widgets.hdf5.tree_viewer import Hdf5TreeViewer
from ....gui.widgets.hdf5.viewer import Hdf5Viewer
from .models.utils import wait_for_loading


@pytest.fixture
def demo_tmpdir(tmp_path, monkeypatch):
    """Generate the demo file in a temporary directory."""
    monkeypatch.setattr(main_module.tempfile, "gettempdir", lambda: str(tmp_path))
    return tmp_path


def _run(monkeypatch, argv, inspect):
    """Run the command line and call `inspect` while the viewer is alive."""
    inspected = {}
    created = []

    def record(cls):
        def factory(*args, **kwargs):
            widget = cls(*args, **kwargs)
            created.append(widget)
            return widget

        return factory

    # Not the top level widgets of the application: widgets of earlier tests
    # linger there, and touching a deleted one raises.
    monkeypatch.setattr(main_module, "Hdf5Viewer", record(Hdf5Viewer))
    monkeypatch.setattr(main_module, "Hdf5TreeViewer", record(Hdf5TreeViewer))

    def fake_exec(self):
        wanted = Hdf5TreeViewer if "--tree-only" in argv else Hdf5Viewer
        viewer = next(
            widget for widget in reversed(created) if isinstance(widget, wanted)
        )
        tree = viewer if isinstance(viewer, Hdf5TreeViewer) else viewer.treeViewer
        wait_for_loading(tree)
        try:
            inspected.update(inspect(viewer, tree))
        finally:
            tree.closeAll()
            viewer.close()
            viewer.deleteLater()
        return 0

    monkeypatch.setattr(qt.QApplication, "exec", fake_exec)
    assert main_module.main(argv) == 0
    qt.QCoreApplication.sendPostedEvents(None, qt.QEvent.Type.DeferredDelete)
    return inspected


def _describe(viewer, tree):
    (h5file,) = tree.h5Files
    return {
        "type": type(viewer).__name__,
        "hasDataPanel": viewer.findChild(DataViewerFrame) is not None,
        "entries": sorted(h5file),
    }


def test_demo_file_plot_types(demo_tmpdir):
    """Verify the demo file holds one NXdata plot type per NXentry."""
    kinds = {}
    with h5py.File(main_module._createDemoFile(), "r") as h5file:
        assert h5file.attrs["NX_class"] == "NXroot"
        for name, entry in h5file.items():
            assert entry.attrs["NX_class"] == "NXentry"
            nxdata = silx.io.nxdata.NXdata(entry["data"])
            assert nxdata.is_valid, name
            kinds[name] = {
                "curve": nxdata.is_curve,
                "image": nxdata.is_image,
                "stack": nxdata.is_stack,
                "scatter": nxdata.is_scatter,
            }

    assert set(kinds) == {"curve", "image", "stack", "scatter"}
    for name, flags in kinds.items():
        assert flags[name], (name, flags)


def test_demo_shows_tree_and_data(ewoksorange_qtapp, demo_tmpdir, monkeypatch):
    """Verify --demo opens the generated file in a viewer with a data panel."""
    inspected = _run(monkeypatch, ["--demo"], _describe)
    assert inspected["type"] == "Hdf5Viewer"
    assert inspected["hasDataPanel"]
    assert inspected["entries"] == ["curve", "image", "scatter", "stack"]


def test_demo_tree_only(ewoksorange_qtapp, demo_tmpdir, monkeypatch):
    """Verify --tree-only opens the tree without a data panel."""
    inspected = _run(monkeypatch, ["--demo", "--tree-only"], _describe)
    assert inspected["type"] == "Hdf5TreeViewer"
    assert not inspected["hasDataPanel"]
    assert inspected["entries"] == ["curve", "image", "scatter", "stack"]


def test_demo_context_menu_actions(ewoksorange_qtapp, demo_tmpdir, monkeypatch):
    """Verify --demo adds a group action and a dataset action."""
    shown = []
    monkeypatch.setattr(
        qt.QMessageBox,
        "information",
        lambda parent, title, text, *args, **kwargs: shown.append(text),
    )

    def inspect(viewer, tree):
        treeView = tree.treeView
        model = treeView.model()
        rootIndex = model.index(0, 0, qt.QModelIndex())
        entryIndex = model.index(0, 0, rootIndex)
        dataIndex = model.index(0, 0, entryIndex)
        signalIndex = [
            model.index(row, 0, dataIndex)
            for row in range(model.rowCount(dataIndex))
            if model.data(model.index(row, 0, dataIndex)) == "signal"
        ][0]

        labels = {}
        for kind, index in (("group", entryIndex), ("dataset", signalIndex)):
            treeView.selectionModel().select(
                index, qt.QItemSelectionModel.ClearAndSelect
            )
            before = set(treeView.findChildren(qt.QMenu))
            treeView._createContextMenu(treeView.visualRect(index).center())
            menus = [m for m in treeView.findChildren(qt.QMenu) if m not in before]
            labels[kind] = [
                action.text()
                for menu in menus
                for action in menu.actions()
                if action.text().startswith(("Count children", "Describe"))
            ]
            for menu in menus:
                for action in menu.actions():
                    if action.text() in labels[kind]:
                        action.trigger()
        return {"labels": labels}

    labels = _run(monkeypatch, ["--demo"], inspect)["labels"]
    assert any(text.startswith("Count children") for text in labels["group"])
    assert not any(text.startswith("Describe") for text in labels["group"])
    assert any(text.startswith("Describe") for text in labels["dataset"])
    assert any("children" in text for text in shown)
    assert any("shape" in text for text in shown)


@pytest.mark.parametrize("access", list(main_module.ACCESS_MODELS))
def test_access_scenarios(ewoksorange_qtapp, demo_tmpdir, monkeypatch, access):
    """Verify every access scenario browses the generated file."""

    def inspect(viewer, tree):
        (h5file,) = tree.h5Files
        return {
            "model": type(tree.treeModel).__name__,
            "entries": sorted(h5file),
            "signal": list(h5file["curve/data/signal"][()][:3]),
        }

    inspected = _run(monkeypatch, ["--demo", "--access", access], inspect)
    assert inspected["model"] == type(main_module.ACCESS_MODELS[access]()).__name__
    assert inspected["entries"] == ["curve", "image", "scatter", "stack"]
    assert len(inspected["signal"]) == 3
