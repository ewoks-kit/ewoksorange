from ewokscore.task import Task
import numpy


class SumList(Task, input_names=["iterable"], output_names=["sum"]):
    def run(self):
        self.outputs.sum = numpy.sum(self.inputs.iterable)
