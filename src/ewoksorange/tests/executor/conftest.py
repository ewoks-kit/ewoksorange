from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Generator
from typing import Tuple

import pytest

from ...gui.concurrency.executor import EwoksExecutor
from ...gui.concurrency.executor import SubmitPolicy
from .signals import SignalRecorder


@pytest.fixture(params=["sync", "thread", "process"])
def executor_context_factory(request):

    kind = request.param

    @contextmanager
    def executor_context(
        policy=SubmitPolicy.ALWAYS, workers=2
    ) -> Generator[Tuple[str, EwoksExecutor, SignalRecorder], None, None]:

        if kind == "sync":
            executor = EwoksExecutor(None, policy)
        elif kind == "thread":
            executor = EwoksExecutor(ThreadPoolExecutor(max_workers=workers), policy)
        else:
            executor = EwoksExecutor(ProcessPoolExecutor(max_workers=workers), policy)

        recorder = SignalRecorder()
        recorder.connect(executor)

        try:
            yield kind, executor, recorder
        finally:
            executor.shutdown(wait=True)

    return executor_context
