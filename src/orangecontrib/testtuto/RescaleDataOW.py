from ewokscore.task import Task
from ewoksorange.bindings.owwidgets import OWEwoksWidgetOneThread

import numpy


class RescaleDataTask(
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
        assert isinstance(percentiles, tuple) and len(percentiles) == 2, "incoherent input"
        assert percentiles[0] <= percentiles[1], "incoherent percentiles value"
        data_min = numpy.percentile(data, percentiles[0])
        data_max = numpy.percentile(data, percentiles[1])

        self.outputs.data = self.rescale_data(
            data=data,
            data_min=data_min,
            data_max=data_max,
        )

    def rescale_data(data, new_min, new_max, data_min=None, data_max=None):
        if data_min is None:
            data_min = numpy.min(data)
        if data_max is None:
            data_max = numpy.max(data)
        return (new_max - new_min) / (data_max - data_min) * (data - data_min) + new_min


class RescaleDataOW(
    OWEwoksWidgetOneThread,
    ewokstaskclass=RescaleDataTask,
):
    name = "rescale data"
    id = "orange.widgets.my_project.RescaleDataWidget"
    description = (
        "widget to rescale data (numpy array) within a percentile range."
    )
    pass
