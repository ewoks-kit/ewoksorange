import numpy
from ewokscore.task import Task

from ewoksorange.bindings.owwidgets import OWEwoksWidgetOneThread


class ClipDataTask(
    Task,
    input_names=["data", "percentiles"],
    output_names=["data"],
):
    """
    Task to rescale 'data' (numpy array) to the given percentiles.
    """

    def run(self):
        data = self.inputs.data
        # compute data min and max
        percentiles = self.inputs.percentiles
        assert (
            isinstance(percentiles, tuple) and len(percentiles) == 2
        ), "incoherent input"
        assert percentiles[0] <= percentiles[1], "incoherent percentiles value"

        self.outputs.data = numpy.clip(
            data,
            a_min=numpy.percentile(data, percentiles[0]),
            a_max=numpy.percentile(data, percentiles[1]),
        )


class ClipDataOW(
    OWEwoksWidgetOneThread,
    ewokstaskclass=ClipDataTask,
):
    name = "rescale data"
    id = "orange.widgets.my_project.ClipDataTask"
    description = "widget to clip data (numpy array) within a percentile range."
    pass
