from ewokscore.task import Task
import numpy


class SumList(Task, input_names=["iterable"], output_names=["sum"]):
    def run(self):
        if self.inputs.iterable is None:
            raise ValueError("iterable / list should be provided")
        self.outputs.sum = numpy.sum(self.inputs.iterable)


class GenerateList(Task, input_names=["length"], output_names=["iterable"]):
    def run(self):
        if self.inputs.length is None:
            raise ValueError("length should be provided")
        self.outputs.iterable = numpy.random.random(self.inputs.length) * 100.0
