from ewoksorange.bindings import OWEwoksWidgetOneThreadPerRun
from ewoksorange.tests.listoperations import SumList2
import logging

_logger = logging.getLogger(__name__)


class SumListSeveralThread(
    OWEwoksWidgetOneThreadPerRun,
    ewokstaskclass=SumList2,
):
    """
    Simple demo class that create a new thread each time an execution of
    SumList2 is required
    """

    name = "SumList on several thread"

    description = "Sum all elements of a list using a new thread for each summation"

    category = "esrfWidgets"

    want_main_area = False
