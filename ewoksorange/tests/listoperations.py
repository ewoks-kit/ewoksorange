from ewokscore.task import Task
import numpy
import logging

_logger = logging.getLogger(__name__)


class PrintSum(Task, input_names=["sum"]):
    def run(self):
        if self.inputs.sum is None:
            raise ValueError("'value' should be provided")
        print("input value is", self.inputs.sum)


class SumList(Task, input_names=["list"], output_names=["sum"]):
    def __init__(self, progress=None, inputs=None, varinfo=None):
        super().__init__(varinfo=varinfo, inputs=inputs)
        self._task_progress = progress

    def update_progress(self, progress):
        if self._task_progress is not None:
            self._task_progress.progress = progress

    def run(self):
        if self.inputs.list is None:
            raise ValueError("list should be provided")
        sum_ = 0
        n_elmt = len(self.inputs.list)
        for i_elmt, elmt in enumerate(self.inputs.list):
            sum_ += elmt
            self.update_progress((i_elmt / n_elmt) * 100.0)
        self.update_progress(100.0)
        self.outputs.sum = sum_


class GenerateList(Task, input_names=["length"], output_names=["list"]):
    def run(self):
        if self.inputs.length is None:
            raise ValueError("length should be provided")
        self.outputs.list = numpy.random.random(self.inputs.length) * 100.0
