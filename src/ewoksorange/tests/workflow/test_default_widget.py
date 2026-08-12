from ewokscore import Task
from ewoksutils.import_utils import qualname

from ...bindings import execute_graph


class Dummy(Task, input_names=["a"], output_names=["b"]):
    def run(self):
        self.outputs.b = self.inputs.a + 1


def test_default_widgets(ewoksorange_qtapp):
    nodes = [
        {
            "id": "task1",
            "task_type": "class",
            "task_identifier": qualname(Dummy),
            "default_inputs": [{"name": "a", "value": 1}],
        },
        {
            "id": "task2",
            "task_type": "class",
            "task_identifier": qualname(Dummy),
        },
    ]

    links = [
        {
            "source": "task1",
            "target": "task2",
            "data_mapping": [{"source_output": "b", "target_input": "a"}],
        }
    ]

    # Create and execute the orange workflow
    graph = {"graph": {"id": "test_graph"}, "nodes": nodes, "links": links}
    results = execute_graph(
        graph, no_gui=True, outputs=[{"all": True}], merge_outputs=False, timeout=10
    )

    assert results == {"task1": {"b": 2}, "task2": {"b": 3}}
