from ewoksorange.bindings import OWEwoksWidgetNoThread
from ewoksorange.tests.listoperations import PrintSum



class PrintSumOW(
    OWEwoksWidgetNoThread,
    ewokstaskclass=PrintSum,
):

    name = "Print list sum"

    description = "Print received list sum"

    want_main_area = False
