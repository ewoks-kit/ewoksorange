"""
clipdata.py: Core code for the ClipDataTask, which is a task to rescale 'data' (numpy array) to the given percentiles.
Includes the ewoks task and the pydantic models.
"""

import numpy
from ewokscore.model import BaseInputModel
from ewokscore.model import BaseOutputModel
from ewokscore.task import Task
from pydantic import Field


class InputModel(BaseInputModel):
    data: numpy.ndarray = Field(..., description="data to rescale")
    percentiles: tuple[float, float] = Field(
        ...,
        description="""percentiles to use for rescaling, must be a tuple of two values (p_min, p_max) with p_min <= p_max""",
    )


class OutputModel(BaseOutputModel):
    data: numpy.ndarray = Field(..., description="rescaled data")


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

        self.outputs.data = numpy.clip(
            data,
            a_min=numpy.percentile(data, percentiles[0]),
            a_max=numpy.percentile(data, percentiles[1]),
        )
