import sys

import h5py
import numpy
import pytest

from ...io.hdf5.static import StaticFile
from .utils import open_from_other_process


@pytest.fixture
def h5file(tmp_path):
    """Create a minimal HDF5 file holding a single dataset."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["existing"] = 42
    return filename


def test_default_open_options(h5file):
    """Verify a file is opened read-only and unlocked by default."""
    opened = {}

    class _TracingFile(StaticFile):
        def open_h5_file(self, filename, **open_options):
            opened[filename] = dict(open_options)
            return super().open_h5_file(filename, **open_options)

    with _TracingFile(h5file) as h5root:
        assert h5root["existing"][()] == 42
        assert opened[h5file] == {"mode": "r", "locking": False}

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OPENED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OPENED"


def test_the_file_is_kept_open(h5file):
    """Verify the file is opened once and closed by close."""
    opened = []

    class _TracingFile(StaticFile):
        def open_h5_file(self, filename, **open_options):
            opened.append(filename)
            return super().open_h5_file(filename, **open_options)

    h5root = _TracingFile(h5file)
    assert h5root["existing"][()] == 42
    assert h5root["existing"][()] == 42
    assert opened == [h5file]

    h5root.close()
    with h5py.File(h5file, "a") as f:
        f["added"] = numpy.arange(3)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
@pytest.mark.parametrize(
    "mode, locking, expected_read, expected_append",
    [
        ("r", False, ("OPENED", "OPENED", "OPENED"), ("OPENED", "OPENED", "OPENED")),
        (
            "r",
            True,
            ("OPENED", "OPENED", "OPENED"),
            ("OSError:LOCKED", "OPENED", "OSError:LOCKED"),
        ),
        (
            "a",
            True,
            ("OSError:LOCKED", "OPENED", "OSError:LOCKED"),
            ("OSError:LOCKED", "OPENED", "OSError:LOCKED"),
        ),
    ],
)
def test_configurable_mode_and_locking(
    h5file, mode, locking, expected_read, expected_append
):
    """Verify configured modes and locked states match expectations."""
    with StaticFile(h5file, mode=mode, locking=locking) as h5root:
        assert h5root["existing"][()] == 42

        assert _external_open(h5file, "r") == expected_read
        assert _external_open(h5file, "a") == expected_append


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
@pytest.mark.parametrize(
    "mode, locking, expected_read, expected_append",
    [
        ("r", False, ("OPENED", "OPENED", "OPENED"), ("OPENED", "OPENED", "OPENED")),
        (
            "r",
            True,
            ("OPENED", "OPENED", "OPENED"),
            ("OSError:LOCKED", "OSError:LOCKED", "OSError:LOCKED"),
        ),
        (
            "a",
            True,
            ("OSError:LOCKED", "OSError:LOCKED", "OSError:LOCKED"),
            ("OSError:LOCKED", "OSError:LOCKED", "OSError:LOCKED"),
        ),
    ],
)
def test_configurable_mode_and_locking_windows(
    h5file, mode, locking, expected_read, expected_append
):
    """Verify configured modes and locked states match expectations."""
    with StaticFile(h5file, mode=mode, locking=locking) as h5root:
        assert h5root["existing"][()] == 42

        assert _external_open(h5file, "r") == expected_read
        assert _external_open(h5file, "a") == expected_append


def test_unlocked_writing_is_refused(h5file):
    """Verify a mode which would corrupt the file is refused."""
    with pytest.raises(ValueError):
        StaticFile(h5file, mode="a", locking=False)


def _external_open(filename: str, mode: str) -> tuple:
    results = open_from_other_process(filename, mode)
    return results.locking, results.not_locking, results.default
