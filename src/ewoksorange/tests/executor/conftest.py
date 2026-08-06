from contextlib import contextmanager
from typing import Generator
from typing import Tuple

import pytest

from ...gui.concurrency.executor import Concurrency
from ...gui.concurrency.executor import EwoksExecutor
from ...gui.concurrency.executor import SubmitPolicy
from ...gui.concurrency.executor import create_pool_executor
from .signals import SignalRecorder


@pytest.fixture(params=list(Concurrency), ids=lambda c: c.name.lower())
def executor_context_factory(request):

    concurrency = request.param
    kind = concurrency.name.lower()

    @contextmanager
    def executor_context(
        policy=SubmitPolicy.ALWAYS, workers=2
    ) -> Generator[Tuple[str, EwoksExecutor, SignalRecorder], None, None]:

        pool = create_pool_executor(concurrency, max_workers=workers)
        executor = EwoksExecutor(pool, policy)

        recorder = SignalRecorder()
        recorder.connect(executor)

        try:
            yield kind, executor, recorder
        finally:
            executor.shutdown(wait=True)

    return executor_context
