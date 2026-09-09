import os
import stat

import h5py
import numpy
import pytest
from silx.io import h5py_utils

from ...io.hdf5.owned import OwnedFile
from .utils import OPENED_IGNORING_LOCK
from .utils import open_from_other_process


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


@pytest.mark.parametrize("keep_open", [False, True])
def test_a_task_can_start_writing_while_it_is_read(h5files, keep_open):
    """Verify reading first does not refuse a task which writes afterwards."""
    master, _ = h5files
    with OwnedFile(master, keep_open=keep_open) as h5root:
        assert h5root["own"][0] == 9

        with h5py_utils.File(master, mode="a") as writer:
            writer["added"] = [1]

        # And what that task wrote is readable through the same view.
        assert "added" in OwnedFile(master)


@pytest.mark.parametrize("keep_open", [False, True])
def test_a_task_writing_already_is_joined(h5files, keep_open):
    """Verify reading a file a task of this process has open for writing."""
    master, _ = h5files
    with h5py_utils.File(master, mode="a") as writer:
        with OwnedFile(master, keep_open=keep_open) as h5root:
            assert h5root["own"][0] == 9

            writer["own"][0] = 8
            writer.flush()
            # The same file, so the write is there without reopening.
            assert h5root["own"][0] == 8


def test_the_file_is_not_written(h5files):
    """Verify the view does not write the file it opens read-write."""
    master, _ = h5files
    with OwnedFile(master, keep_open=True) as h5root:
        with pytest.raises(RuntimeError):
            h5root.create_group("new")
        assert sorted(h5root) == ["linked", "own"]


def test_read_only_files_are_still_readable(tmp_path, file_permissions):
    """Verify a file which cannot be opened read-write is read read-only."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["data"] = [1, 2, 3]

    os.chmod(filename, stat.S_IREAD)
    try:
        with OwnedFile(filename, keep_open=True) as h5root:
            assert h5root["data"][()].tolist() == [1, 2, 3]
    finally:
        os.chmod(filename, stat.S_IWRITE | stat.S_IREAD)


def test_another_process_cannot_write_it(h5files):
    """Verify the file is claimed for this process while it is read."""
    master, _ = h5files
    with OwnedFile(master, keep_open=True) as h5root:
        assert h5root["own"][0] == 9

        # Owned means no other process writes it, so taking the lock is free.
        external_append = open_from_other_process(master, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.default == "OSError:LOCKED"
        # Reading unlocked elsewhere stays possible where the lock allows it.
        external_read = open_from_other_process(master, mode="r")
        assert external_read.not_locking == OPENED_IGNORING_LOCK


def test_reads_the_master_and_its_links(h5files):
    """Verify external links are read read-only, the master read-write."""
    master, target = h5files
    opened = {}

    class _TracingFile(OwnedFile):
        def open_h5_file(self, filename, **open_options):
            h5file = super().open_h5_file(filename, **open_options)
            opened[filename] = h5file.mode
            return h5file

        def open_external_h5_file(self, filename, **open_options):
            h5file = super().open_external_h5_file(filename, **open_options)
            opened[filename] = h5file.mode
            return h5file

    with _TracingFile(master) as h5root:
        assert h5root["own"][0] == 9
        assert numpy.array_equal(h5root["linked/data"][()], [0, 1, 2, 3])
        assert opened[master] == "r+"
        assert opened[target] == "r"


def test_read_while_writing_the_master(tmp_path, file_permissions):
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


@pytest.mark.parametrize("h5path", ["/external/data", "/virtual/data"])
def test_read_target_while_writing_the_master(tmp_path, file_permissions, h5path):
    """Verify data of a file this process cannot write is readable, whichever
    way it is reached, while the master is open for writing.
    """
    target = str(tmp_path / "target.h5")
    with h5py.File(target, "w") as f:
        f["/group/data"] = [4.0, 5.0, 6.0]

    master = str(tmp_path / "master.h5")
    with h5py.File(master, "w") as f:
        f["/external/data"] = h5py.ExternalLink("target.h5", "/group/data")
        layout = h5py.VirtualLayout(shape=(3,), dtype=float)
        layout[:] = h5py.VirtualSource(target, "/group/data", shape=(3,))
        f.create_virtual_dataset("/virtual/data", layout, fillvalue=numpy.nan)

    os.chmod(target, stat.S_IREAD)
    try:
        with OwnedFile(master, keep_open=True) as h5root:
            assert numpy.array_equal(h5root[h5path][()], [4, 5, 6])
    finally:
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)


def test_soft_link_to_an_external_link(tmp_path, file_permissions):
    """Verify a soft link whose target is an external link is followed into
    that file, the way a Bliss scan reaches its raw data.
    """
    target = str(tmp_path / "raw.h5")
    with h5py.File(target, "w") as f:
        f["/entry/data"] = [4.0, 5.0, 6.0]

    master = str(tmp_path / "master.h5")
    with h5py.File(master, "w") as f:
        f["/1.1/instrument/detector/data"] = h5py.ExternalLink("raw.h5", "/entry/data")
        f["/1.1/measurement/detector"] = h5py.SoftLink("/1.1/instrument/detector/data")
        f["/1.1/measurement/sibling"] = h5py.ExternalLink("raw.h5", "/entry/data")
        f["/1.1/measurement/relative"] = h5py.SoftLink("sibling")

    # The master is claimed for writing and the raw data cannot be written, so
    # h5py following the links itself would open the raw data in the wrong mode.
    os.chmod(target, stat.S_IREAD)
    try:
        with OwnedFile(master, keep_open=True) as h5root:
            measurement = h5root["/1.1/measurement"]
            assert sorted(measurement) == ["detector", "relative", "sibling"]
            for name in measurement:
                assert measurement[name][()].tolist() == [4.0, 5.0, 6.0]
    finally:
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)


def test_a_link_in_a_circle_is_skipped(tmp_path, caplog):
    """Verify links pointing at each other do not hang the read."""
    filename = str(tmp_path / "circular.h5")
    with h5py.File(filename, "w") as f:
        f["data"] = [1]
        f["first"] = h5py.SoftLink("/second")
        f["second"] = h5py.SoftLink("/first")

    with caplog.at_level("WARNING"):
        with OwnedFile(filename) as h5root:
            assert sorted(h5root) == ["data"]
