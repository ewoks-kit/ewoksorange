from AnyQt.QtCore import QObject
import time
from ewoksorange.bindings.taskexecutor import TaskExecutor
from ewoksorange.bindings.taskexecutor import ThreadedTaskExecutor
from ewoksorange.bindings.taskexecutor_queue import TaskExecutorQueue
from ewoksorange.bindings.qtapp import QtEvent
from ewokscore import Task
from ewokscore.tests.examples.tasks.sumtask import SumTask


def test_task_executor():
    executor = TaskExecutor(SumTask)
    assert not executor.has_task
    assert not executor.succeeded

    executor.create_task(inputs={"a": 1, "b": 2})
    assert executor.has_task
    assert not executor.succeeded

    executor.execute_task()
    assert executor.succeeded
    results = {k: v.value for k, v in executor.output_variables.items()}
    assert results == {"result": 3}


def test_threaded_task_executor(qtapp):
    finished = QtEvent()

    def finished_callback():
        finished.set()

    executor = ThreadedTaskExecutor(ewokstaskclass=SumTask)

    executor.finished.connect(finished_callback)
    assert not executor.has_task
    assert not executor.succeeded

    executor.create_task(inputs={"a": 1, "b": 2})
    assert executor.has_task
    assert not executor.succeeded

    executor.start()
    assert finished.wait(timeout=3)
    assert executor.succeeded
    results = {k: v.value for k, v in executor.output_variables.items()}
    assert results == {"result": 3}

    executor.finished.disconnect(finished_callback)


def test_threaded_task_executor_queue(qtapp):
    class MyObject(QObject):
        def __init__(self):
            self.results = None
            self.finished = QtEvent()

        def finished_callback(self):
            # task_executor = self.sender()  # Doesn't work for unknown reasons
            task_executor = executor._task_executor
            self.results = {
                k: v.value for k, v in task_executor.output_variables.items()
            }
            self.finished.set()

    obj = MyObject()
    executor = TaskExecutorQueue(ewokstaskclass=SumTask)
    executor.add(inputs={"a": 1, "b": 2}, _callbacks=(obj.finished_callback,))
    assert obj.finished.wait(timeout=3)
    assert obj.results == {"result": 3}


def test_threaded_task_executor_queue_stop_current_task(qtapp):
    """test an 'infinite' task that we want to kill and launch another task behind"""

    class MyObject(QObject):
        def __init__(self):
            self.results = None
            self.finished = QtEvent()

        def finished_callback(self):
            # task_executor = self.sender()  # Doesn't work for unknown reasons
            task_executor = executor._task_executor
            self.results = {
                k: v.value for k, v in task_executor.output_variables.items()
            }
            self.finished.set()

    class InfinitProcess(Task, input_names=["duration"], output_names=["result"]):
        def run(self):
            time.sleep(self.inputs.duration)
            self.outputs.result = f"have waited {self.inputs.duration}s"

    executor = TaskExecutorQueue(ewokstaskclass=InfinitProcess)

    obj1 = MyObject()
    obj2 = MyObject()

    # test adding two jobs first
    executor.add(
        inputs={
            "duration": 10,
        },
        _callbacks=(obj1.finished_callback,),
    )
    executor.add(
        inputs={
            "duration": 1,
        },
        _callbacks=(obj2.finished_callback,),
    )
    assert not executor.is_available
    executor.stop_current_task(wait=False)
    assert obj2.finished.wait(timeout=3)
    assert obj1.results is None
    assert obj2.results["result"] == "have waited 1s"

    # then try to resend the job with obj1
    executor.add(
        inputs={
            "duration": 0.2,
        },
        _callbacks=(obj1.finished_callback,),
    )
    assert obj1.finished.wait(timeout=3)
    assert obj1.results["result"] == "have waited 0.2s"

    assert executor.is_available
