import os
import sys

import pytest


@pytest.fixture
def file_permissions() -> None:
    """Skip when file permissions cannot make a file unwritable."""
    if sys.platform == "win32":
        pytest.skip("Windows has no POSIX file permission bits")
    if os.geteuid() == 0:
        pytest.skip("root ignores file permission bits")
