import warnings

__all__ = [
    "convert_graph",
    "execute_graph",
    "graph_is_supported",
    "load_graph",
    "save_graph",
]


def __getattr__(name):
    """Lazy import with deprecation warning."""
    if name not in __all__:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

    from . import bindings

    warnings.warn(
        f"Accessing '{name}' from '{__name__}' is deprecated and will be "
        "removed in a future release. Please import it from "
        "'ewoksorange.bindings' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return getattr(bindings, name)
