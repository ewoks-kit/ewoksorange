from ewoksorange.bindings import OWEwoksWidgetWithTaskStack
from ewoksorange.tests.listoperations import SumList3
import logging

_logger = logging.getLogger(__name__)


class SumListWithTaskStack(
    OWEwoksWidgetWithTaskStack,
    ewokstaskclass=SumList3,
):
    """
    Simple demo class that will process task with a FIFO stack and one thread
    connected with the stack
    """

    name = "SumList with one thread and a stack"

    description = "Sum all elements of a list using a thread and a stack"

    category = "esrfWidgets"

    want_main_area = False
