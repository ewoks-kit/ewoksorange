from ewoksorange.registration import get_owwidget_descriptions


def test_orangecontrib_packages(register_ewoks_example_addons):
    from orangecontrib import ewoks_example_supercategory  # noqa F401
    from orangecontrib.evaluate import ewoks_example_submodule  # noqa F401
    from orangecontrib import ewoks_example_category  # noqa F401
    from orangecontrib import list_operations  # noqa F401


def test_discover_widgets(register_ewoks_example_addons):
    widgets = get_owwidget_descriptions()
    discovered = set(w.id for w in widgets)
    expected = {
        "orangecontrib.ewoks_example_supercategory.ewoks_example_subcategory.adder1",
        "orangecontrib.ewoks_example_supercategory.ewoks_example_subcategory.adder2",
        "orangecontrib.evaluate.ewoks_example_submodule.adder1",
        "orangecontrib.evaluate.ewoks_example_submodule.adder2",
        "orangecontrib.ewoks_example_category.adder1",
        "orangecontrib.ewoks_example_category.adder2",
        "orangecontrib.list_operations.listgenerator",
        "orangecontrib.list_operations.print_sum",
        "orangecontrib.list_operations.sumlist_one_thread",
        "orangecontrib.list_operations.sumlist_several_thread",
        "orangecontrib.list_operations.sumlist_stack",
    }
    assert (discovered & expected) == expected
