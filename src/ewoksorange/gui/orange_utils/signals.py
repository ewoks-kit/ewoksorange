from orangewidget.widget import Input as _Input
from orangewidget.widget import InputSignal as _InputSignal  # noqa F401
from orangewidget.widget import Output as _Output
from orangewidget.widget import OutputSignal as _OutputSignal  # noqa F401


class Input(_Input):
    def __init__(self, name, type, *args, ewoksname: str = "", **kwargs) -> None:
        super().__init__(name, type, *args, **kwargs)
        self.ewoksname = ewoksname


class Output(_Output):
    def __init__(self, name, type, *args, ewoksname: str = "", **kwargs) -> None:
        super().__init__(name, type, *args, **kwargs)
        self.ewoksname = ewoksname
