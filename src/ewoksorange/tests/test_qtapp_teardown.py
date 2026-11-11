import logging
import sys
import weakref

from ewoksorange_pytest_plugin.qtapp_teardown import _global_cleanup_pytest


class _Object:
    pass


def test_global_cleanup_pytest_releases_log_record_tracebacks():
    try:
        raise RuntimeError("error")
    except RuntimeError:
        record = logging.LogRecord(
            "name", logging.ERROR, __file__, 1, "msg", None, sys.exc_info()
        )
    assert record.exc_info is not None

    _global_cleanup_pytest()

    assert record.exc_info is None


def test_global_cleanup_pytest_with_dead_weakref_proxy():
    # Some libraries keep proxies of objects that no longer exist
    # (e.g. llvmlite, used by numba). `isinstance` raises `ReferenceError` on them.
    obj = _Object()
    dead_proxies = [weakref.proxy(obj), weakref.proxy(lambda: None)]
    del obj

    _global_cleanup_pytest()

    assert len(dead_proxies) == 2
