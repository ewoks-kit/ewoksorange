import re
from contextlib import ExitStack
from contextlib import contextmanager
from typing import Iterator
from typing import Optional
from typing import Type


def assert_exception(
    exception: BaseException, exc_type: Type[BaseException], match: Optional[str] = None
) -> None:
    assert isinstance(exception, exc_type), (
        f"Expected {exc_type.__name__}, got {type(exception).__name__}: {exception}"
    )

    if match is not None:
        ex_message = str(exception)
        assert re.search(match, ex_message), (
            f"Exception message {ex_message!r} does not match pattern {match!r}."
        )


@contextmanager
def assert_none_emitted(qtbot, *signals) -> Iterator[None]:
    """Fail when any of `signals` is emitted within the context."""
    with ExitStack() as stack:
        for signal in signals:
            stack.enter_context(qtbot.assert_not_emitted(signal))
        yield
