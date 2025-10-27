from orangecontrib.ewoksdemo.sumtask import OWSumTask

from .utils import execute_task


def test_sumtask_task():
    result = execute_task(OWSumTask.ewokstaskclass, inputs={"a": 1, "b": 2})
    assert result == {"result": 3}


def test_sumtask_widget(qtapp):
    result = execute_task(OWSumTask, inputs={"a": 1, "b": 2})
    assert result == {"result": 3}
