import warnings

from .widgets.simple_types_mixin import SimpleTypesWidgetMixin  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.widgets.simple_types_mixin' module.",
    DeprecationWarning,
    stacklevel=2,
)
