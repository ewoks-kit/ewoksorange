import re
from collections import defaultdict
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

from ewokscore.variable import VariableContainer

from ...gui.concurrency.executor import EwoksExecutor
from ...gui.concurrency.executor import TaskFuture
from ...gui.qt_utils.app import wait_until

EventsType = Dict[str, List[Optional[TaskFuture]]]


class SignalRecorder:
    def __init__(self):
        self._events: EventsType = defaultdict(list)
        self._order: List[str] = []
        self._default_counts = {
            "submitted": 0,
            "started": 0,
            "succeeded": 0,
            "failed": 0,
            "aborted": 0,
            "finished": 0,
            "ignored": 0,
        }

    def connect(self, executor: EwoksExecutor) -> None:
        executor.submitted.connect(self._store_future("submitted"))
        executor.started.connect(self._store_future("started"))
        executor.succeeded.connect(self._store_future("succeeded"))
        executor.failed.connect(self._store_future("failed"))
        executor.aborted.connect(self._store_future("aborted"))
        executor.finished.connect(self._store_future("finished"))
        executor.ignored.connect(self._store_noargs("ignored"))

    def _store_future(self, name: str) -> Callable[[TaskFuture], None]:
        def callback(future: TaskFuture):
            print(f"Signal {name!r} received")
            self._events[name].append(future)
            self._order.append(name)

        return callback

    def _store_noargs(self, name: str) -> Callable[[], None]:
        def callback():
            print(f"Signal {name!r} received")
            self._events[name].append(None)
            self._order.append(name)

        return callback

    def count(self, name: str) -> int:
        return len(self._events[name])

    def future(self, name: str, index: int = 0) -> TaskFuture:
        """Return the future carried by the `index`-th `name` signal."""
        return self._events[name][index]

    def assert_counts(self, **expected) -> None:
        expected = {**self._default_counts, **expected}
        actual = {name: self.count(name) for name in expected}
        assert actual == expected

    def assert_order(self, *expected: str) -> None:
        assert self._order == list(expected)

    def assert_succeeded(self, future: TaskFuture, result: VariableContainer) -> None:
        events = [event for event in self._events["succeeded"] if event is future]
        assert len(events) == 1, (
            f"Expected one succeeded signal for {future!r}, got {len(events)}."
        )
        assert future.result() == result

    def assert_failed(
        self, future: TaskFuture, exc_type: Type[Exception], match: Optional[str] = None
    ) -> None:
        events = [event for event in self._events["failed"] if event is future]

        assert len(events) == 1, (
            f"Expected one failed signal for {future!r}, got {len(events)}."
        )

        exception = future.exception()
        assert isinstance(exception, exc_type), (
            f"Expected {exc_type.__name__}, got {type(exception).__name__}: {exception}"
        )

        if match is not None:
            ex_message = str(exception)
            assert re.search(match, ex_message), (
                f"Exception message {ex_message!r} does not match pattern {match!r}."
            )

    def assert_finished(self, future: TaskFuture) -> None:
        assert future in self._events["finished"]

    def assert_started(self, future: TaskFuture) -> None:
        assert future in self._events["started"]

    def wait_for(self, name: str, count: int = 1, timeout: float = 5.0) -> None:
        assert wait_until(lambda: len(self._events[name]) >= count, timeout=timeout)

    def wait_future(
        self, name: str, index: int = 0, timeout: float = 5.0
    ) -> TaskFuture:
        """Wait for the `index`-th `name` signal and return its future."""
        self.wait_for(name, count=index + 1, timeout=timeout)
        return self.future(name, index=index)
