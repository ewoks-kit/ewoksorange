import pytest
from ewoksutils.import_utils import import_qualname
from ewoksorange.tests.utils import execute_task

_WIDGETS = [
    "orangecontrib.list_operations.sumlist_one_thread.SumListOneThread",
    "orangecontrib.list_operations.sumlist_several_thread.SumListSeveralThread",
    "orangecontrib.list_operations.sumlist_stack.SumListWithTaskStack",
]


@pytest.mark.parametrize("widget_qualname", _WIDGETS)
def test_sumlist(widget_qualname, register_ewoks_example_2_addon):
    widget = import_qualname(widget_qualname)
    result = execute_task(widget, inputs={"list": [1, 2, 3]})
    assert result == {"sum": 6}
    result = execute_task(widget.ewokstaskclass, inputs={"list": [1, 2, 3]})
    assert result == {"sum": 6}


def test_listgenerator(register_ewoks_example_2_addon):
    widget_qualname = "orangecontrib.list_operations.listgenerator.ListGenerator"
    widget = import_qualname(widget_qualname)
    result = execute_task(widget, inputs={"length": 7})
    assert len(result["list"]) == 7
    result = execute_task(widget.ewokstaskclass, inputs={"length": 7})
    assert len(result["list"]) == 7


def test_printsum(register_ewoks_example_2_addon):
    widget_qualname = "orangecontrib.list_operations.print_sum.PrintSumOW"
    widget = import_qualname(widget_qualname)
    result = execute_task(widget, inputs={"sum": 99})
    assert result == {}
    result = execute_task(widget.ewokstaskclass, inputs={"sum": 99})
    assert result == {}
