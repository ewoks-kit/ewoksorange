import time

from AnyQt.QtCore import QObject
from ewokscore import Task
from ewokscore.missing_data import MISSING_DATA
from ewokscore.tests.examples.tasks.sumtask import SumTask

from ..gui.concurrency.base import TaskExecutor
from ..gui.concurrency.queued import TaskExecutorQueue
from ..gui.concurrency.threaded import ThreadedTaskExecutor
from ..gui.qt_utils.app import QtEvent


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


def test_cancel_current_task_in_task_executor_queue(qtapp):
    """test an 'infinite' task that we want to kill and launch another task behind"""

    class MyObject(QObject):
        """
        Object containing a callback function ('finished_callback'). This callback function is called when the task has been executed by the task executor
        """

        def __init__(self):
            self.results = None
            self.finished = QtEvent()

        def finished_callback(self):
            # task_executor = self.sender()  # Doesn't work for unknown reasons
            task_executor = executor._task_executor
            # copy the task output variables
            self.results = {
                k: v.value for k, v in task_executor.output_variables.items()
            }
            self.finished.set()

    class InfiniteTask(Task, input_names=["duration"], output_names=["result"]):
        def run(self):
            time.sleep(self.inputs.duration)
            self.outputs.result = f"have waited {self.inputs.duration}s"

        def cancel(self):
            self._cancel = True

    executor = TaskExecutorQueue(ewokstaskclass=InfiniteTask)

    obj1 = MyObject()
    obj2 = MyObject()
    obj3 = MyObject()

    # test adding two tasks to the executor.
    # expected behavior:
    # the first task is cancelled (so result is MISSING_DATA)
    # then the second task is executed (results is 'have waited 1s')
    executor.add(
        inputs={
            "duration": 100,
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
    # cancel obj 1
    executor.cancel_running_task(wait=False)
    assert obj2.finished.wait(timeout=30)
    assert obj1.results["result"] is MISSING_DATA
    assert executor.is_available
    assert obj2.results["result"] == "have waited 1s"

    # then try to sending an new job
    executor.add(
        inputs={
            "duration": 0.2,
        },
        _callbacks=(obj3.finished_callback,),
    )
    assert obj3.finished.wait()
    assert obj3.results["result"] == "have waited 0.2s"

    assert executor.is_available
