from contextlib import contextmanager
from typing import Dict
from typing import Iterator

from ...gui.concurrency.executor import EwoksExecutor

EXECUTOR_SIGNALS = (
    "submitted",
    "aboutToStart",
    "started",
    "succeeded",
    "failed",
    "cancelled",
    "stopRequested",
    "aborted",
    "killed",
    "finished",
    "ignored",
)


@contextmanager
def assert_signal_counts(
    qtbot, executor: EwoksExecutor, timeout: int = 10_000, **expected: int
) -> Iterator[None]:
    """Fail unless each signal of `executor` is emitted within the context
    exactly as many times as given in `expected`, and never when not given.

    On leaving the context, it waits up to `timeout` milliseconds for the
    signals that are still being delivered.
    """
    unknown = set(expected) - set(EXECUTOR_SIGNALS)
    assert not unknown, f"Unknown executor signals: {sorted(unknown)}"
    expected = {**dict.fromkeys(EXECUTOR_SIGNALS, 0), **expected}
    counts: Dict[str, int] = dict.fromkeys(EXECUTOR_SIGNALS, 0)

    slots = []
    for name in EXECUTOR_SIGNALS:

        def slot(*_, name=name) -> None:
            counts[name] += 1

        getattr(executor, name).connect(slot)
        slots.append((name, slot))

    try:
        yield
        try:
            qtbot.wait_until(lambda: counts == expected, timeout=timeout)
        except qtbot.TimeoutError:
            pass  # the assertion below shows the difference
        assert counts == expected
    finally:
        for name, slot in slots:
            getattr(executor, name).disconnect(slot)
