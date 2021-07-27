from ewokscore.task import Task
import numpy


class SumList(Task, input_names=["iterable"], output_names=["sum"]):
    def update_progress(self, progress):
        pass

    def run(self):
        if self.inputs.iterable is None:
            raise ValueError("iterable / list should be provided")
        sum_ = 0
        n_elmt = len(self.inputs.iterable)
        for i_elmt, elmt in enumerate(self.inputs.iterable):
            sum_ += elmt
            self.update_progress((i_elmt / n_elmt) * 100.0)
        self.update_progress(100.0)

        self.outputs.sum = sum_


class GenerateList(Task, input_names=["length"], output_names=["iterable"]):
    def run(self):
        if self.inputs.length is None:
            raise ValueError("length should be provided")
        self.outputs.iterable = numpy.random.random(self.inputs.length) * 100.0
