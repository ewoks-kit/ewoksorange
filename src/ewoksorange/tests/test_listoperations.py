import pytest
from ewoksutils.import_utils import import_qualname

from .utils import execute_task

_WIDGETS = [
    "orangecontrib.ewokstest.sumlist_one_thread.SumListOneThread",
    "orangecontrib.ewokstest.sumlist_several_thread.SumListSeveralThread",
    "orangecontrib.ewokstest.sumlist_stack.SumListWithTaskStack",
]


@pytest.mark.parametrize("widget_qualname", _WIDGETS)
def test_sumlist(widget_qualname, qtapp):
    widget = import_qualname(widget_qualname)
    result = execute_task(widget, inputs={"list": [1, 2, 3]})
    assert result == {"sum": 6}
    result = execute_task(widget.ewokstaskclass, inputs={"list": [1, 2, 3]})
    assert result == {"sum": 6}


def test_listgenerator(qtapp):
    widget_qualname = "orangecontrib.ewokstest.listgenerator.ListGenerator"
    widget = import_qualname(widget_qualname)
    result = execute_task(widget, inputs={"length": 7})
    assert len(result["list"]) == 7
    result = execute_task(widget.ewokstaskclass, inputs={"length": 7})
    assert len(result["list"]) == 7


def test_printsum(qtapp):
    widget_qualname = "orangecontrib.ewokstest.print_sum.PrintSumOW"
    widget = import_qualname(widget_qualname)
    result = execute_task(widget, inputs={"sum": 99})
    assert result == {}
    result = execute_task(widget.ewokstaskclass, inputs={"sum": 99})
    assert result == {}
