"""
clipdata.py: Core code for the ClipDataTask, which is a task to rescale 'data' (numpy array) to the given percentiles.
Includes the ewoks task and the pydantic models.
"""

import numpy
from ewokscore.model import BaseInputModel
from ewokscore.model import BaseOutputModel
from ewokscore.task import Task


class InputModel(BaseInputModel):
    data: numpy.ndarray
    """data to rescale"""
    percentiles: tuple[float, float]
    """percentiles to use for rescaling, must be a tuple of two values (p_min, p_max) with p_min <= p_max"""


class OutputModel(BaseOutputModel):
    data: numpy.ndarray
    """rescaled data"""


class ClipDataTask(
    Task,
    input_model=InputModel,
    output_model=OutputModel,
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
