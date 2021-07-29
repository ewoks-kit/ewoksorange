from ewoksorange.bindings import OWEwoksWidgetOneThread
from ewoksorange.tests.listoperations import SumList
import logging

_logger = logging.getLogger(__name__)


class SumListOneThread(
    OWEwoksWidgetOneThread,
    ewokstaskclass=SumList,
):

    name = "SumList one thread"

    description = "Sum all elements of a list using at most one thread"

    category = "esrfWidgets"

    want_main_area = False
