import json

import pytest

from ewoksorange.gui.canvas import menu
from ewoksorange.gui.canvas.handler import OrangeCanvasHandler
from ewoksorange.orange_version import ORANGE_VERSION


def test_exported_json_matches_manual_workflow(tmp_path, ewoksorange_qtapp):
    destination_path = tmp_path / "exported_workflow.json"
    graph = {
        "nodes": [
            {
                "id": "source",
                "task_type": "class",
                "task_identifier": "ewokscore.tests.examples.tasks.sumtask.SumTask",
            },
            {
                "id": "sink",
                "task_type": "class",
                "task_identifier": "ewokscore.tests.examples.tasks.sumtask.SumTask",
            },
        ],
        "links": [
            {
                "source": "source",
                "target": "sink",
                "data_mapping": [{"source_output": "result", "target_input": "a"}],
            }
        ],
    }

    source_path = tmp_path / "source_workflow.json"

    with open(source_path, "w") as f:
        json.dump(graph, f)

    # Here i import to the canvas then re export it and verify the exported json.

    with OrangeCanvasHandler() as handler:
        menu._import_ewoks_workflow(handler.canvas, str(source_path))
        menu._export_ewoks_workflow(handler.canvas, str(destination_path))

        with open(destination_path) as f:
            exported_workflow = json.load(f)

        assert exported_workflow["nodes"][0]["id"] == "source"
        assert exported_workflow["nodes"][1]["id"] == "sink"
        assert exported_workflow["links"] == graph["links"]


@pytest.mark.skipif(
    ORANGE_VERSION == ORANGE_VERSION.latest_oasys, reason="OASYS2 has its own dialog"
)
def test_open_dialog_has_ewoks_filter(ewoksorange_qtapp):
    menu.add_ewoks_file_filters()
    with OrangeCanvasHandler() as handler:
        dialog = handler.canvas._open_workflow_dialog()
        assert menu._FILTER in dialog.nameFilters()


@pytest.mark.skipif(
    ORANGE_VERSION != ORANGE_VERSION.latest_oasys, reason="OASYS2 specific"
)
def test_oasys_open_dialog_has_ewoks_filter(monkeypatch, ewoksorange_qtapp):
    from oasys2.canvas.application.canvasmain import OASYSMainWindow

    menu.add_ewoks_file_filters()
    filters = []

    def get_open_file_name(parent, caption, directory, name_filter, *args):
        filters.append(name_filter)
        return "", ""

    monkeypatch.setattr(menu.QFileDialog, "getOpenFileName", get_open_file_name)
    OASYSMainWindow()._open_scheme()
    assert menu._FILTER in filters[0]
