from ewoksorange.gui.simpletypesmixin import SimpleTypesWidgetMixin
from ewokscore import missing_data


def serialize_list(value) -> str:
    if missing_data.is_missing_data(value):
        return value
    else:
        return f"<List length={len(value)}>"


class WidgetMixin(SimpleTypesWidgetMixin):
    def _get_parameter_options(self, name):
        if name == "list":
            return {"serialize": serialize_list}
        elif name == "sum":
            return {"value_for_type": 0.0}
        elif name == "length":
            return {"value_for_type": 0}
        else:
            return dict()
