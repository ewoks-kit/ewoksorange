from AnyQt.QtCore import QTimer
from orangecanvas.scheme import Scheme
from orangecanvas.scheme import SchemeLink
from orangecanvas.scheme.signalmanager import SignalManager

from ..concurrency.executor import TaskFuture
from ..orange_utils.orange_imports import gui
from .parameter_form import ParameterForm


class SimpleTypesWidgetMixin:
    def __init__(self):
        super().__init__()
        self._init_control_area()
        self._init_main_area()
        self.task_executor.succeeded.connect(self._update_output_form)

        # This is a bit hacky: When a widget is created, the widget is not included in the scheme, so we must delay the links initialization.
        QTimer.singleShot(0, self.__init_links)

    def __init_links(self):
        scheme: Scheme = self.__getSheme()
        scheme.link_added.connect(self.__onLinkAdded)
        scheme.link_removed.connect(self.__onLinkRemoved)
        for link in scheme.links:
            self.__onLinkAdded(link)

    def __getSheme(self) -> Scheme:
        signalManager = getattr(self, "signalManager", None)
        if signalManager is None:
            raise AttributeError(
                "SimpleTypesWidgetMixin assumes an Orange Widget with a signalManager attribute."
            )
        if not isinstance(signalManager, SignalManager):
            raise TypeError(
                f"signalManager expected type is `SignalManager` but is `{type(signalManager)}`"
            )

        return signalManager.scheme()

    def _init_control_area(self):
        super()._init_control_area()
        box = gui.widgetBox(self.controlArea, "Default Inputs")
        self._default_inputs_form = ParameterForm(parent=box)

        for name, value in self.get_default_input_values(include_missing=True).items():
            options = self._get_parameter_options(name)
            self._default_inputs_form.addParameter(
                name,
                value=value,
                value_change_callback=self._default_inputs_changed,
                **options,
            )

        box = gui.widgetBox(self.controlArea, "Inputs From Previous Task")
        self._dynamic_input_form = ParameterForm(parent=box)
        for name in self.get_input_names():
            options = self._get_parameter_options(name)
            self._dynamic_input_form.addParameter(
                name, readonly=True, enabled=False, **options
            )

    def _init_main_area(self):
        super()._init_main_area()
        box = gui.widgetBox(self.mainArea, "Outputs")
        self._output_form = ParameterForm(parent=box)
        for name in self.get_output_names():
            options = self._get_parameter_options(name)
            self._output_form.addParameter(name, readonly=True, **options)

    def _get_parameter_options(self, name):
        return {}

    def _default_inputs_changed(self):
        self.update_default_inputs(**self._default_inputs_form.get_parameter_values())

    def handleNewSignals(self):
        for name, value in self.get_dynamic_input_values().items():
            self._dynamic_input_form.set_parameter_value(name, value)

        super().handleNewSignals()

    def __onLinkRemoved(self, link: SchemeLink):
        scheme = self.__getSheme()
        if scheme.widget_for_node(link.sink_node) is self:
            self._default_inputs_form.set_parameter_enabled(link.sink_channel.id, True)
            self._dynamic_input_form.set_parameter_enabled(link.sink_channel.id, False)

    def __onLinkAdded(self, link: SchemeLink):
        scheme = self.__getSheme()
        if scheme.widget_for_node(link.sink_node) is self:
            self._default_inputs_form.set_parameter_enabled(link.sink_channel.id, False)
            self._dynamic_input_form.set_parameter_enabled(link.sink_channel.id, True)

    def _update_output_form(self, task_future: TaskFuture) -> None:
        for name, value in task_future.output_values().items():
            self._output_form.set_parameter_value(name, value)


class IntegerAdderMixin(SimpleTypesWidgetMixin):
    def _get_parameter_options(self, name):
        return {"value_for_type": 0}
