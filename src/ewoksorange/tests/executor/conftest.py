from contextlib import contextmanager
from typing import Callable
from typing import Generator
from typing import Tuple

import pytest

from ...gui.concurrency.executor import Concurrency
from ...gui.concurrency.executor import EwoksExecutor
from ...gui.concurrency.executor import SubmitPolicy
from ...gui.concurrency.executor import create_pool_executor

pytest.register_assert_rewrite("ewoksorange.tests.executor.utils")


@pytest.fixture(params=list(Concurrency), ids=lambda c: c.name.lower())
def executor_context_factory(qtbot, request):

    concurrency = request.param
    kind = concurrency.name.lower()

    @contextmanager
    def executor_context(
        policy=SubmitPolicy.ALWAYS, workers=2
    ) -> Generator[Tuple[str, EwoksExecutor], None, None]:

        pool = create_pool_executor(concurrency, max_workers=workers)
        executor = EwoksExecutor(pool, policy)

        try:
            yield kind, executor
        finally:
            executor.shutdown(wait=True)

    return executor_context


@pytest.fixture
def executor_factory(
    qtbot,
) -> Generator[Callable[[Concurrency, SubmitPolicy, int], EwoksExecutor], None, None]:
    """Return a factory function to create an `EwoksExecutor` with the given concurrency, policy and number of workers."""
    executors = []

    def _executor_factory(
        concurrency: Concurrency, policy=SubmitPolicy.ALWAYS, workers=2
    ) -> EwoksExecutor:
        pool = create_pool_executor(concurrency, max_workers=workers)
        executor = EwoksExecutor(pool, policy)
        executors.append(executor)
        return executor

    try:
        yield _executor_factory
    finally:
        for executor in executors:
            executor.shutdown(wait=True)
