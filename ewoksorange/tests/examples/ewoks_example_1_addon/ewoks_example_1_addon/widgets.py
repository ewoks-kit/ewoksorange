from ewoksorange.gui.simpletypesmixin import SimpleTypesWidgetMixin


class IntegerAdderMixin(SimpleTypesWidgetMixin):
    def _get_parameter_options(self, name):
        return {"value_for_type": 0}
