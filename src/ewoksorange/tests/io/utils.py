"""Helpers shared by the tests reading HDF5 files."""

import subprocess
import sys
from dataclasses import dataclass

OPENED_IGNORING_LOCK = "OSError:LOCKED" if sys.platform == "win32" else "OPENED"
"""What opening a file locked by this process yields when the opener takes no
lock itself: POSIX file locks are advisory, so the open succeeds, while Windows
file locks are mandatory, so it is refused.
"""

_EXTERNAL_OPEN = """
import sys
import h5py

for locking in (True, False, None):
    try:
        with h5py.File(sys.argv[1], mode=sys.argv[2], locking=locking):
            print("OPENED")
    except OSError:
        print("OSError:LOCKED")
"""


@dataclass(frozen=True)
class ExternalOpenResults:
    locking: str
    not_locking: str
    default: str


def open_from_other_process(filename: str, mode: str) -> ExternalOpenResults:
    """Attempt to open `filename` from a separate process."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _EXTERNAL_OPEN, filename, mode],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return ExternalOpenResults(*result.stdout.split())
