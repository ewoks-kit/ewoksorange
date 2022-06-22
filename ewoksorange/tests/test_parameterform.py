import json
from functools import partial
from ewokscore import missing_data
from ..gui.parameterform import ParameterForm


def test_parameterform(qtapp):
    while qtapp.hasPendingEvents():
        qtapp.processEvents()

    nchanged = dict()

    def cb(name):
        nchanged.setdefault(name, 0)
        nchanged[name] += 1

    form = ParameterForm()

    form.addParameter("string", value_change_callback=partial(cb, "string"))
    form.addParameter(
        "integer", value_for_type=0, value_change_callback=partial(cb, "integer")
    )
    form.addParameter(
        "float", value_for_type=0.0, value_change_callback=partial(cb, "float")
    )
    form.addParameter(
        "boolean", value_for_type=False, value_change_callback=partial(cb, "boolean")
    )
    form.addParameter(
        "json",
        serialize=json.dumps,
        deserialize=json.loads,
        value_change_callback=partial(cb, "json"),
    )
    form.addParameter(
        "choice",
        value_for_type=["choice1", "choice2"],
        value_change_callback=partial(cb, "choice"),
    )

    values = form.get_parameter_values()
    expected = {
        "string": missing_data.MISSING_DATA,
        "integer": missing_data.MISSING_DATA,
        "float": missing_data.MISSING_DATA,
        "boolean": missing_data.MISSING_DATA,
        "json": missing_data.MISSING_DATA,
        "choice": missing_data.MISSING_DATA,
    }
    assert values == expected
    assert not nchanged

    # Set string widget value from code
    form.set_parameter_value("string", "abc")
    assert form.get_parameter_value("string") == "abc"

    form.set_parameter_value("string", missing_data.MISSING_DATA)
    assert form.get_parameter_value("string") == missing_data.MISSING_DATA

    # Set integer widget value from code
    form.set_parameter_value("integer", 10)
    assert form.get_parameter_value("integer") == 10

    form.set_parameter_value("integer", missing_data.MISSING_DATA)
    assert form.get_parameter_value("integer") == missing_data.MISSING_DATA

    # Set float widget value from code
    form.set_parameter_value("float", 20.0)
    assert form.get_parameter_value("float") == 20.0

    form.set_parameter_value("float", missing_data.MISSING_DATA)
    assert form.get_parameter_value("float") == missing_data.MISSING_DATA

    # Set boolean widget value from code
    form.set_parameter_value("boolean", True)
    assert form.get_parameter_value("boolean") is True

    form.set_parameter_value("boolean", missing_data.MISSING_DATA)
    assert form.get_parameter_value("boolean") == missing_data.MISSING_DATA

    # Set json widget value from code
    form.set_parameter_value("json", {"a": 1})
    assert form.get_parameter_value("json") == {"a": 1}

    form.set_parameter_value("json", missing_data.MISSING_DATA)
    assert form.get_parameter_value("json") == missing_data.MISSING_DATA

    # Set choice widget value from code
    form.set_parameter_value("choice", "choice2")
    assert form.get_parameter_value("choice") == "choice2"

    form.set_parameter_value("choice", missing_data.MISSING_DATA)
    assert form.get_parameter_value("choice") == missing_data.MISSING_DATA

    while qtapp.hasPendingEvents():
        qtapp.processEvents()

    # form.show()
    # qtapp.exec()

    expected = {
        "string": missing_data.MISSING_DATA,
        "integer": missing_data.MISSING_DATA,
        "float": missing_data.MISSING_DATA,
        "boolean": missing_data.MISSING_DATA,
        "json": missing_data.MISSING_DATA,
        "choice": missing_data.MISSING_DATA,
    }
    assert values == expected
    assert not nchanged

    # Set string widget wrong value from code
    form.set_parameter_value("string", "abc")
    assert form.get_parameter_value("string") == "abc"

    form.set_parameter_value("string", 10)
    assert form.get_parameter_value("string") == missing_data.MISSING_DATA

    # Set integer widget wrong value from code
    form.set_parameter_value("integer", -99)
    assert form.get_parameter_value("integer") == -99

    form.set_parameter_value("integer", "wrong")
    assert form.get_parameter_value("integer") == missing_data.MISSING_DATA

    # Set float widget wrong value from code
    form.set_parameter_value("float", 20.0)
    assert form.get_parameter_value("float") == 20.0

    form.set_parameter_value("float", "wrong")
    assert form.get_parameter_value("float") == missing_data.MISSING_DATA

    # Set boolean widget wrong value from code
    form.set_parameter_value("boolean", True)
    assert form.get_parameter_value("boolean") is True

    form.set_parameter_value("boolean", "wrong")
    assert form.get_parameter_value("boolean") == missing_data.MISSING_DATA

    # Set json widget wrong value from code
    form.set_parameter_value("json", {"a": 1})
    assert form.get_parameter_value("json") == {"a": 1}

    form.set_parameter_value("json", object)
    assert form.get_parameter_value("json") == missing_data.MISSING_DATA

    # Set choice widget wrong value from code
    form.set_parameter_value("choice", "choice2")
    assert form.get_parameter_value("choice") == "choice2"

    form.set_parameter_value("choice", "wrong")
    assert form.get_parameter_value("choice") == missing_data.MISSING_DATA
