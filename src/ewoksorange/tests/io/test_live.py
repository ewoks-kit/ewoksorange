import logging
import os
import stat

import h5py
import numpy
import pytest
from silx.io import h5py_utils

from ...io.hdf5.access import read_access
from ...io.hdf5.live import LiveDataset
from ...io.hdf5.live import LiveFile
from ...io.hdf5.live import LiveGroup
from ...io.hdf5.owned import OwnedFile


@pytest.fixture
def h5file(tmp_path):
    """Create a file with a group, a dataset and attributes."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f.attrs["creator"] = "test"
        group = f.create_group("entry")
        group.attrs["NX_class"] = "NXentry"
        dataset = group.create_dataset("data", data=numpy.arange(6.0).reshape(2, 3))
        dataset.attrs["units"] = "mm"
    return filename


@pytest.fixture
def h5files(tmp_path):
    """Create a file with an external link to a second file."""
    target = str(tmp_path / "target.h5")
    with h5py.File(target, "w") as f:
        f["entry/data"] = numpy.arange(4)

    master = str(tmp_path / "master.h5")
    with h5py.File(master, "w") as f:
        f["own"] = [9]
        f["linked"] = h5py.ExternalLink("target.h5", "/entry")
    return master, target


def test_structure_is_proxied(h5file):
    """Verify groups, datasets and attributes are exposed."""
    h5root = LiveFile(h5file)

    assert h5root.attrs["creator"] == "test"

    group = h5root["entry"]
    assert isinstance(group, LiveGroup)
    assert group.attrs["NX_class"] == "NXentry"

    dataset = group["data"]
    assert isinstance(dataset, LiveDataset)
    assert dataset.shape == (2, 3)
    assert dataset.ndim == 2
    assert dataset.dtype == numpy.float64
    assert len(dataset) == 2
    assert dataset.attrs["units"] == "mm"
    assert numpy.array_equal(dataset[()], numpy.arange(6.0).reshape(2, 3))
    assert numpy.array_equal(dataset[0], [0.0, 1.0, 2.0])
    assert numpy.array_equal(numpy.array(dataset), dataset[()])


def test_file_is_not_held_open(h5file):
    """Verify another writer can modify the file while it is proxied."""
    dataset = LiveFile(h5file)["entry/data"]
    assert dataset[0, 0] == 0.0

    # Exclusive write access while the proxy exists.
    with h5py.File(h5file, "a", locking=True) as f:
        f["entry/data"][0, 0] = 42.0

    assert dataset[0, 0] == 42.0


def test_external_link_uses_its_own_file(h5files):
    """Verify a dataset behind an external link reads from the linked file."""
    master, target = h5files
    h5root = LiveFile(master)

    assert sorted(h5root) == ["linked", "own"]
    dataset = h5root["linked/data"]
    assert numpy.array_equal(dataset[()], [0, 1, 2, 3])

    with h5py.File(target, "a", locking=True) as f:
        f["entry/data"][0] = 7

    assert numpy.array_equal(dataset[()], [7, 1, 2, 3])


def test_external_open_options(h5files):
    """Verify external links are opened with their own options."""
    master, target = h5files
    opened = {}

    class _TracingFile(LiveFile):
        def open_h5_file(self, filename, **open_options):
            opened[filename] = dict(open_options)
            return super().open_h5_file(filename, **open_options)

    h5root = _TracingFile(
        master, external_open_options={"mode": "r", "locking": False}, mode="r"
    )
    assert h5root["linked/data"][0] == 0

    assert opened[master] == {"mode": "r"}
    assert opened[target] == {"mode": "r", "locking": False}


def test_read_access_while_open_for_writing(h5file):
    """Verify a file open for writing in this process stays readable."""
    with h5py.File(h5file, "a") as writer:
        writer["entry/data"][0, 0] = 5.0
        writer.flush()

        with read_access(h5file) as h5read:
            assert h5read["entry/data"][0, 0] == 5.0


def test_read_access_file_follows_links_read_only(h5files):
    """Verify OwnedFile reads the master and its external links."""
    master, target = h5files
    opened = {}

    class _TracingFile(OwnedFile):
        def open_h5_file(self, filename, **open_options):
            h5file = super().open_h5_file(filename, **open_options)
            opened[filename] = h5file.mode
            return h5file

    h5root = _TracingFile(master)
    assert h5root["own"][0] == 9
    assert numpy.array_equal(h5root["linked/data"][()], [0, 1, 2, 3])
    assert opened[master] == "r"
    assert opened[target] == "r"


def test_read_access_file_while_writing_the_master(tmp_path, file_permissions):
    """Verify a master this process writes exposes its read-only links."""
    target = str(tmp_path / "target.h5")
    with h5py.File(target, "w") as f:
        f["entry/data"] = numpy.arange(4)

    master = str(tmp_path / "master.h5")
    with h5py.File(master, "w") as f:
        f["linked"] = h5py.ExternalLink("target.h5", "/entry")

    os.chmod(target, stat.S_IREAD)
    try:
        with h5py_utils.File(master, mode="a") as writer:
            writer["own"] = [9]

            h5root = OwnedFile(master)
            assert sorted(h5root) == ["linked", "own"]
            assert numpy.array_equal(h5root["linked/data"][()], [0, 1, 2, 3])
    finally:
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)


def test_broken_external_link_is_skipped(tmp_path, caplog):
    """Verify a link to a missing file does not hide the rest of the file."""
    master = str(tmp_path / "master.h5")
    with h5py.File(master, "w") as f:
        f["own"] = [9]
        f["gone"] = h5py.ExternalLink("missing.h5", "/entry")
        f["gone_path"] = h5py.ExternalLink("master.h5", "/absent")

    with caplog.at_level(logging.WARNING):
        h5root = LiveFile(master)

    assert sorted(h5root) == ["own"]
    assert h5root["own"][0] == 9
    assert len([r for r in caplog.records if "Skipping" in r.message]) == 2
    assert not os.path.exists(str(tmp_path / "missing.h5"))


def test_reading_leaves_no_handle_open(tmp_path):
    """Verify a proxy holds no handle, so the file stays writable and grows."""
    filename = str(tmp_path / "grows.h5")
    with h5py.File(filename, "w") as f:
        f["first"] = [1, 2, 3]

    h5root = LiveFile(filename)
    assert sorted(h5root) == ["first"]
    assert h5root["first"][()].tolist() == [1, 2, 3]

    # No handle is left open, so this process can still write the file. A
    # handle kept open by the proxy would make this raise.
    with h5py.File(filename, "a") as f:
        f["second"] = [4, 5, 6]

    # And a later read sees what that writer committed.
    assert sorted(LiveFile(filename)) == ["first", "second"]
