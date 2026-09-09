import os
import subprocess
import sys

import h5py
import numpy
import pytest
from silx.io import h5py_utils

from ...io.hdf5.access import process_open_mode
from ...io.hdf5.access import read_access
from ...io.hdf5.links import ReadOnlyLinksFile

_EXTERNAL_WRITER = """
import sys
import time
from silx.io import h5py_utils

with h5py_utils.File(sys.argv[1], mode="a") as f:
    f["collected"] = list(range(10))
    f.flush()
    print("WRITING", flush=True)
    time.sleep(float(sys.argv[2]))
"""


@pytest.fixture
def h5file(tmp_path):
    """Create a file with a dataset."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["existing"] = numpy.arange(3)
    return filename


def test_no_writer(h5file):
    """Verify a file nobody writes is opened read-only and unlocked."""
    assert process_open_mode(h5file) is None
    with read_access(h5file) as h5read:
        assert h5read.mode == "r"
        assert numpy.array_equal(h5read["existing"][()], [0, 1, 2])


def test_writer_in_this_process(h5file):
    """Verify the file this process writes is read through the same mode."""
    with h5py_utils.File(h5file, mode="a") as writer:
        assert process_open_mode(h5file) == "r+"

        with read_access(h5file) as h5read:
            # The locking flags of two handles on one file must match.
            assert h5read.mode == "r+"
            assert numpy.array_equal(h5read["existing"][()], [0, 1, 2])

        writer["added"] = 1
        with read_access(h5file) as h5read:
            assert "added" in h5read

    assert process_open_mode(h5file) is None


def test_writer_in_another_process(h5file):
    """Verify a file being written elsewhere is readable without locking it."""
    with subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", _EXTERNAL_WRITER, h5file, "10"],
        stdout=subprocess.PIPE,
        text=True,
    ) as writer:
        try:
            assert writer.stdout.readline().strip() == "WRITING"
            # The current process holds no handle, so the writer is elsewhere.
            assert process_open_mode(h5file) is None

            with read_access(h5file, retry_timeout=10) as h5read:
                assert h5read.mode == "r"
                assert numpy.array_equal(h5read["collected"][()], list(range(10)))
        finally:
            writer.kill()


def test_read_access_is_read_only(h5file):
    """Verify another mode is refused."""
    with pytest.raises(ValueError):
        with read_access(h5file, mode="a"):
            pass


def test_links_from_a_file_we_write(tmp_path):
    """Verify links are not locked when reading a file this process writes."""
    target = str(tmp_path / "raw.h5")
    with h5py.File(target, "w") as f:
        f["counters/diode"] = numpy.arange(4)

    results = str(tmp_path / "results.h5")
    with h5py.File(results, "w") as f:
        f["raw"] = h5py.ExternalLink("raw.h5", "/counters")

    with h5py_utils.File(results, mode="a") as writer:
        writer["fit"] = [1.0]

        with ReadOnlyLinksFile(results) as h5file:
            assert h5file.mode == "r+"
            assert numpy.array_equal(h5file["raw/diode"][()], [0, 1, 2, 3])
            # The linked raw data is neither written nor locked.
            assert h5file["raw"].file.mode == "r"

            with subprocess.Popen(  # noqa: S603
                [sys.executable, "-c", _EXTERNAL_WRITER, target, "0"],
                stdout=subprocess.PIPE,
                text=True,
            ) as other:
                assert other.stdout.readline().strip() == "WRITING"
                assert other.wait(timeout=30) == 0
            assert os.path.exists(target)


def test_missing_file(tmp_path):
    """Verify reading a file which does not exist does not create it."""
    filename = str(tmp_path / "missing.h5")
    with pytest.raises(OSError):
        with read_access(filename):
            pass
    assert not os.path.exists(filename)
