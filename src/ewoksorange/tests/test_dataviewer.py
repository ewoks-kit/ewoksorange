import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass

import h5py
import pytest

from ..gui.widgets.data_viewer import DataViewer

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


def _open_from_other_process(filename, mode: str) -> ExternalOpenResults:
    """Attempt to open `filename` from a separate process."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _EXTERNAL_OPEN, filename, mode],
        capture_output=True,
        text=True,
    )
    return ExternalOpenResults(*result.stdout.split())


@contextmanager
def _data_viewer(**kwargs):
    """Create a `DataViewer` and guarantee its files are closed afterwards."""
    viewer = DataViewer(None, **kwargs)
    try:
        yield viewer
    finally:
        viewer.closeAll()
        viewer.close()


@pytest.fixture
def h5file(tmp_path):
    """Create a minimal HDF5 file holding a single dataset."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["existing"] = 42
    return filename


def test_default_mode_and_locking(qtapp, h5file):
    """Verify DataViewer has append mode and locking enabled by default."""
    with _data_viewer() as viewer:
        assert viewer._mode == "a"
        assert viewer._locking is None

        viewer.updateFile(h5file)
        (h5,) = viewer._h5files
        assert h5.mode == "r+"
        assert h5["existing"][()] == 42

        external_read = _open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OSError:LOCKED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OSError:LOCKED"

        external_append = _open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OSError:LOCKED"


def test_configurable_mode_and_locking(qtapp, h5file):
    """Verify configured modes and locked states match expectations."""

    # #########################
    # Read-Only Mode
    # #########################
    with _data_viewer(mode="r", locking=False) as viewer:
        viewer.updateFile(h5file)
        (h5,) = viewer._h5files
        assert h5.mode == "r"
        assert h5["existing"][()] == 42

        external_read = _open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = _open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OPENED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OPENED"

    with _data_viewer(mode="r", locking=True) as viewer:
        viewer.updateFile(h5file)
        (h5,) = viewer._h5files
        assert h5.mode == "r"
        assert h5["existing"][()] == 42

        external_read = _open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = _open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OSError:LOCKED"

    with _data_viewer(mode="r") as viewer:
        viewer.updateFile(h5file)
        (h5,) = viewer._h5files
        assert h5.mode == "r"
        assert h5["existing"][()] == 42

        external_read = _open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = _open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OSError:LOCKED"

    # #########################
    # Append Mode
    # #########################
    with _data_viewer(mode="a", locking=False) as viewer:
        viewer.updateFile(h5file)
        (h5,) = viewer._h5files
        assert h5.mode == "r+"
        assert h5["existing"][()] == 42

        external_read = _open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = _open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OPENED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OPENED"

    with _data_viewer(mode="a", locking=True) as viewer:
        viewer.updateFile(h5file)
        (h5,) = viewer._h5files
        assert h5.mode == "r+"
        assert h5["existing"][()] == 42

        external_read = _open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OSError:LOCKED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OSError:LOCKED"

        external_append = _open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OSError:LOCKED"

    with _data_viewer(mode="a") as viewer:
        viewer.updateFile(h5file)
        (h5,) = viewer._h5files
        assert h5.mode == "r+"
        assert h5["existing"][()] == 42

        external_read = _open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OSError:LOCKED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OSError:LOCKED"

        external_append = _open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OSError:LOCKED"
