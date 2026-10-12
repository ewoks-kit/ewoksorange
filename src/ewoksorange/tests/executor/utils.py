import re
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
