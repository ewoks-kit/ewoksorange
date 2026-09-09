import h5py
import numpy
import pytest

from ...io.hdf5 import live
from ...io.hdf5.live import LiveFile
from .utils import open_from_other_process


@pytest.fixture
def h5file(tmp_path):
    """Create a file with a dataset."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["entry/data"] = numpy.arange(6.0).reshape(2, 3)
    return filename


def test_default_open_options(h5file):
    """Verify a file is read read-only and unlocked."""
    opened = {}

    class _TracingFile(LiveFile):
        def open_h5_file(self, filename, **open_options):
            opened[filename] = dict(open_options)
            return super().open_h5_file(filename, **open_options)

    h5root = _TracingFile(h5file)
    assert h5root["entry/data"][0, 0] == 0.0
    assert opened[h5file] == {"mode": "r", "locking": False}


def test_file_is_not_held_open(h5file):
    """Verify another writer can modify the file while it is proxied."""
    dataset = LiveFile(h5file)["entry/data"]
    assert dataset[0, 0] == 0.0

    # Exclusive write access while the proxy exists.
    with h5py.File(h5file, "a", locking=True) as f:
        f["entry/data"][0, 0] = 42.0

    assert dataset[0, 0] == 42.0


def test_a_writer_can_still_start(h5file):
    """Verify another process can open the file for writing while it is read."""
    h5root = LiveFile(h5file)
    assert h5root["entry/data"][0, 0] == 0.0

    external_append = open_from_other_process(h5file, mode="a")
    assert external_append.locking == "OPENED"
    assert external_append.not_locking == "OPENED"
    assert external_append.default == "OPENED"


def test_retry_options_are_passed_on(tmp_path, monkeypatch):
    """Verify reads can be retried while a writer is flushing."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["data"] = [1, 2, 3]

    retry_options = {}
    original = live.retry_open

    def _tracing_retry_open(filename, **options):
        retry_options.update(
            {k: v for k, v in options.items() if k.startswith("retry_")}
        )
        return original(filename, **options)

    monkeypatch.setattr(live, "retry_open", _tracing_retry_open)

    h5root = LiveFile(filename, retry_timeout=5, retry_period=0.1)
    assert h5root["data"][()].tolist() == [1, 2, 3]
    assert retry_options == {"retry_timeout": 5, "retry_period": 0.1}


def test_retry_period_is_optional(tmp_path):
    """Verify a retry timeout can be given on its own."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["data"] = [1, 2, 3]

    h5root = LiveFile(filename, retry_timeout=5)
    assert h5root["data"][()].tolist() == [1, 2, 3]
