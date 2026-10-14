import json

from ewoksorange.gui.canvas import menu
from ewoksorange.gui.canvas.handler import OrangeCanvasHandler


def test_exported_json_matches_manual_workflow(
    tmp_path, monkeypatch, ewoksorange_qtapp
):
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
        monkeypatch.setattr(
            menu.QFileDialog,
            "getOpenFileName",
            lambda *args, **kwargs: (str(source_path), ""),
        )

        menu._import_ewoks_workflow(handler.canvas)

        monkeypatch.setattr(
            menu.QFileDialog,
            "getSaveFileName",
            lambda *_args, **_kwargs: (str(destination_path), ""),
        )
        menu._export_ewoks_workflow(handler.canvas)

        with open(destination_path) as f:
            exported_workflow = json.load(f)

        assert exported_workflow["nodes"][0]["id"] == "source"
        assert exported_workflow["nodes"][1]["id"] == "sink"
        assert exported_workflow["links"] == graph["links"]
