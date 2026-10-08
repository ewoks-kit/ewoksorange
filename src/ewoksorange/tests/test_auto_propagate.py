from AnyQt.QtTest import QSignalSpy
from ewokscore.model import BaseInputModel
from ewokscore.task import Task

from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread


class Inputs(BaseInputModel):
    foo: int


class DummyTask(
    Task,
    input_model=Inputs,
):
    def run(self):
        pass


class EwoksDummyWidget(OWEwoksWidgetNoThread, ewokstaskclass=DummyTask):
    name = "ewoks dummy widget"


def test_auto_execute_enabled(ewoksorange_qtapp):
    widget = EwoksDummyWidget()
    task_submitted_spy = QSignalSpy(widget.task_executor.submitted)
    # New inputs -> task submitted
    widget.handleNewSignals()
    assert len(task_submitted_spy) == 1


def test_auto_execute_disabled(ewoksorange_qtapp):
    widget = EwoksDummyWidget()
    widget.auto_execute = False
    task_submitted_spy = QSignalSpy(widget.task_executor.submitted)
    # New inputs -> task not submitted
    widget.handleNewSignals()
    assert len(task_submitted_spy) == 0
