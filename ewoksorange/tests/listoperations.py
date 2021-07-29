from ewokscore.task import Task
import numpy


class PrintSum(Task, input_names=["sum"]):
    def run(self):
        if self.inputs.sum is None:
            raise ValueError("'value' should be provided")
        print("input value is", self.inputs.sum)


class SumList(Task, input_names=["list"], output_names=["sum"]):
    def update_progress(self, progress):
        pass

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
