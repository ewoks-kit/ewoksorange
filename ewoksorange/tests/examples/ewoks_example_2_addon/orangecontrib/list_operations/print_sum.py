from ewoksorange.bindings import OWEwoksWidgetNoThread
from ewoksorange.tests.listoperations import PrintSum
import logging

_logger = logging.getLogger(__name__)


class PrintSumOW(
    OWEwoksWidgetNoThread,
    ewokstaskclass=PrintSum,
):

    name = "Print list sum"

    description = "Print received list sum"

    category = "esrfWidgets"

    want_main_area = False
