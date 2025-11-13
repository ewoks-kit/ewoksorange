from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from orangewidget.widget import InputSignal as _InputSignal
    from orangewidget.widget import OutputSignal as _OutputSignal
    from orangewidget.widget import Single as _Single

    class Input:
        def __init__(
            self,
            name,
            type,
            handler: str = "",
            flags=_Single,
            id=None,
            doc=None,
            ewoksname: str = "",
        ):
            self._named_tuple = _InputSignal(
                name, type, handler, flags=flags, id=id, doc=doc
            )
            self.ewoksname = ewoksname
            self._seq_id = 0

        def __call__(self, method: callable) -> callable:
            name, type, handler, *args = self.as_tuple()
            handler = method.__name__
            self._named_tuple = _InputSignal(name, type, handler, *args)
            return method

        def __getattr__(self, name):
            return getattr(self._named_tuple, name)

        def as_tuple(self) -> tuple:
            return tuple(self._named_tuple)

        def as_dict(self) -> dict:
            return self._named_tuple._asdict()

    class Output:

        def __init__(
            self, name, type, flags=_Single, id=None, doc=None, ewoksname: str = ""
        ):
            self._named_tuple = _OutputSignal(name, type, flags=flags, id=id, doc=doc)
            self.ewoksname = ewoksname
            self._seq_id = 0

        def __getattr__(self, name):
            return getattr(self._named_tuple, name)

        def as_tuple(self) -> tuple:
            return tuple(self._named_tuple)

        def as_dict(self) -> dict:
            return self._named_tuple._asdict()

else:
    from orangewidget.widget import Input as _Input
    from orangewidget.widget import InputSignal as _InputSignal
    from orangewidget.widget import Output as _Output
    from orangewidget.widget import OutputSignal as _OutputSignal

    class Input(_Input):
        def __init__(self, name, type, *args, ewoksname: str = "", **kwargs) -> None:
            super().__init__(name, type, *args, **kwargs)
            self.ewoksname = ewoksname

    class Output(_Output):
        def __init__(self, name, type, *args, ewoksname: str = "", **kwargs) -> None:
            super().__init__(name, type, *args, **kwargs)
            self.ewoksname = ewoksname
