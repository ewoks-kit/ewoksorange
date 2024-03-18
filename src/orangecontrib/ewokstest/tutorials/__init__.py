try:
    from .. import widget_discovery  # noqa F401
except ImportError:
    pass
else:
    raise RuntimeError("ewokstest is disabled")
