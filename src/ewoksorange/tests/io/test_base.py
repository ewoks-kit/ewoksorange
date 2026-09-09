import logging
import os
import stat
import tempfile

import h5py
import numpy
import pytest

from ...io.hdf5.base import Hdf5Dataset
from ...io.hdf5.base import Hdf5File
from ...io.hdf5.base import Hdf5Group


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
    """Create a file with an external and a soft link to a second file."""
    target = str(tmp_path / "target.h5")
    with h5py.File(target, "w") as f:
        f["entry/data"] = numpy.arange(4)
        f["entry"].attrs["NX_class"] = "NXentry"

    master = str(tmp_path / "master.h5")
    with h5py.File(master, "w") as f:
        f["own"] = [9]
        f["linked"] = h5py.ExternalLink("target.h5", "/entry")
        f["soft"] = h5py.SoftLink("/own")
    return master, target


def test_structure_is_proxied(h5file):
    """Verify groups, datasets and attributes are exposed."""
    h5root = Hdf5File(h5file)

    assert h5root.attrs["creator"] == "test"

    group = h5root["entry"]
    assert isinstance(group, Hdf5Group)
    assert group.attrs["NX_class"] == "NXentry"

    dataset = group["data"]
    assert isinstance(dataset, Hdf5Dataset)
    assert dataset.shape == (2, 3)
    assert dataset.ndim == 2
    assert dataset.dtype == numpy.float64
    assert len(dataset) == 2
    assert dataset.attrs["units"] == "mm"
    assert numpy.array_equal(dataset[()], numpy.arange(6.0).reshape(2, 3))
    assert numpy.array_equal(dataset[0], [0.0, 1.0, 2.0])
    assert numpy.array_equal(numpy.array(dataset), dataset[()])


def test_links_are_followed(h5files):
    """Verify both link kinds lead to their content."""
    master, _ = h5files
    with Hdf5File(master) as h5root:
        assert sorted(h5root) == ["linked", "own", "soft"]
        assert h5root["own"][0] == 9
        assert h5root["soft"][0] == 9
        assert h5root["linked"].attrs["NX_class"] == "NXentry"
        assert numpy.array_equal(h5root["linked/data"][()], [0, 1, 2, 3])
        assert h5root.filename == master


def test_external_link_uses_its_own_file(h5files):
    """Verify a dataset behind an external link reads from the linked file."""
    master, target = h5files
    h5root = Hdf5File(master)

    dataset = h5root["linked/data"]
    assert numpy.array_equal(dataset[()], [0, 1, 2, 3])

    with h5py.File(target, "a", locking=True) as f:
        f["entry/data"][0] = 7

    assert numpy.array_equal(dataset[()], [7, 1, 2, 3])


def test_external_open_options(h5files):
    """Verify external links are opened with their own options."""
    master, target = h5files
    opened = {}

    class _TracingFile(Hdf5File):
        def open_h5_file(self, filename, **open_options):
            opened[filename] = dict(open_options)
            return super().open_h5_file(filename, **open_options)

    h5root = _TracingFile(
        master, external_open_options={"mode": "r", "locking": False}, mode="r"
    )
    assert h5root["linked/data"][0] == 0

    assert opened[master] == {"mode": "r"}
    assert opened[target] == {"mode": "r", "locking": False}


def test_external_open_hook(h5files):
    """Verify linked files can be opened by their own method."""
    master, target = h5files
    opened = []

    class _TracingFile(Hdf5File):
        def open_external_h5_file(self, filename, **open_options):
            opened.append(filename)
            return super().open_external_h5_file(filename, **open_options)

    h5root = _TracingFile(master, mode="r")
    assert h5root["linked/data"][0] == 0
    assert set(opened) == {target}


def test_broken_external_link_is_skipped(tmp_path, caplog):
    """Verify a link to a missing file does not hide the rest of the file."""
    master = str(tmp_path / "master.h5")
    with h5py.File(master, "w") as f:
        f["own"] = [9]
        f["gone"] = h5py.ExternalLink("missing.h5", "/entry")
        f["gone_path"] = h5py.ExternalLink("master.h5", "/absent")

    with caplog.at_level(logging.WARNING):
        h5root = Hdf5File(master)

    assert sorted(h5root) == ["own"]
    assert h5root["own"][0] == 9
    assert len([r for r in caplog.records if "Skipping" in r.message]) == 2
    assert not os.path.exists(str(tmp_path / "missing.h5"))


def test_file_is_not_held_open_by_default(tmp_path):
    """Verify a view holds no handle, so the file stays writable and grows."""
    filename = str(tmp_path / "grows.h5")
    with h5py.File(filename, "w") as f:
        f["first"] = [1, 2, 3]

    h5root = Hdf5File(filename)
    assert sorted(h5root) == ["first"]
    assert h5root["first"][()].tolist() == [1, 2, 3]

    # No handle is left open, so this process can still write the file. A
    # handle kept open by the view would make this raise.
    with h5py.File(filename, "a") as f:
        f["second"] = [4, 5, 6]

    # And a later read sees what that writer committed.
    assert sorted(Hdf5File(filename)) == ["first", "second"]


def test_keep_open_holds_one_handle(tmp_path):
    """Verify a file kept open is opened once and closed by close."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["data"] = [1, 2, 3]

    opened = []

    class _TracingFile(Hdf5File):
        def open_h5_file(self, filename, **open_options):
            opened.append(filename)
            return super().open_h5_file(filename, **open_options)

    h5root = _TracingFile(filename, keep_open=True, mode="r", locking=False)
    assert h5root["data"][()].tolist() == [1, 2, 3]
    assert h5root["data"][()].tolist() == [1, 2, 3]
    assert opened == [filename]

    # A handle kept open in this process refuses a second one in append mode.
    with pytest.raises(OSError):
        h5py.File(filename, "a")

    h5root.close()
    with h5py.File(filename, "a") as f:
        f["more"] = [4]


def test_content_is_re_read_on_every_access(tmp_path):
    """Verify dataset content comes from the file on every access."""
    filename = str(tmp_path / "grows.h5")
    with h5py.File(filename, "w") as f:
        f["data"] = numpy.zeros(3)

    h5root = Hdf5File(filename)
    assert h5root["data"][()].tolist() == [0.0, 0.0, 0.0]

    with h5py.File(filename, "a") as f:
        f["data"][:] = [7, 8, 9]

    assert h5root["data"][()].tolist() == [7.0, 8.0, 9.0]


def test_structure_is_read_per_group_when_first_looked_at(tmp_path):
    """Verify a group not looked at yet shows what the writer added since."""
    filename = str(tmp_path / "grows.h5")
    with h5py.File(filename, "w") as f:
        f["visited/data"] = numpy.arange(3)
        f.create_group("untouched")

    h5root = Hdf5File(filename)
    assert sorted(h5root["visited"]) == ["data"]

    with h5py.File(filename, "a") as f:
        f["visited/late"] = [1]
        f["untouched/late"] = [1]
        f["added"] = [1]

    # Looked at for the first time now, so it is read now.
    assert sorted(h5root["untouched"]) == ["late"]
    # Read already, so it stays as it was read.
    assert sorted(h5root["visited"]) == ["data"]
    # The root was read when its children were first asked for.
    assert "added" not in h5root
    assert "added" in Hdf5File(filename)


def test_is_read_only(h5file):
    """Verify the view of a file cannot write it, whatever its mode."""
    with Hdf5File(h5file, mode="a") as h5root:
        with pytest.raises(RuntimeError):
            h5root.create_group("new")
        with pytest.raises(RuntimeError):
            h5root["entry"].create_dataset("new", data=[1])


@pytest.fixture(params=["absolute", "relative"])
def read_only_target(request, tmp_path, file_permissions):
    """Create a file linking to a second file which cannot be written."""
    target = str(tmp_path / "target.h5")
    with h5py.File(target, "w") as f:
        f["/group/data"] = [4, 5, 6]

    if request.param == "absolute":
        source = target
    else:
        source = os.path.relpath(target, str(tmp_path))

    master = str(tmp_path / "master.h5")
    with h5py.File(master, "w") as f:
        f["/internal/data"] = [1, 2, 3]
        f["/external1"] = h5py.ExternalLink(source, "/")
        f["/external2/data"] = h5py.ExternalLink(source, "/group/data")

        layout = h5py.VirtualLayout(shape=(3,), dtype=float)
        layout[:] = h5py.VirtualSource(source, "/group/data", shape=(3,))
        f.create_virtual_dataset("/virtual/data", layout, fillvalue=numpy.nan)

        layout = h5py.VirtualLayout(shape=(3,), dtype=float)
        layout[:] = h5py.VirtualSource(".", "/internal/data", shape=(3,))
        f.create_virtual_dataset("/internal/virtual/data", layout, fillvalue=numpy.nan)

    os.chmod(target, stat.S_IREAD)
    yield master, target
    os.chmod(target, stat.S_IWRITE | stat.S_IREAD)


def test_read_through_links(read_only_target):
    """Verify linked content is readable while the master is open for writing."""
    master, _ = read_only_target
    with h5py.File(master, "a"):
        with Hdf5File(
            master, mode="a", external_open_options={"mode": "r", "locking": False}
        ) as h5root:
            assert "/internal/data" in h5root
            assert h5root["/internal/data"][()].tolist() == [1, 2, 3]
            assert "/external1/group/data" in h5root
            assert h5root["/external1/group/data"][()].tolist() == [4, 5, 6]
            assert "/external2/data" in h5root
            assert h5root["/external2/data"][()].tolist() == [4, 5, 6]

            assert "/internal/notexisting" not in h5root
            assert "/external1/group" in h5root
            assert "/external1/group/notexisting" not in h5root
            assert "/external2/notexisting" not in h5root


_VIRTUAL_SOURCE_LOCKING = h5py.version.hdf5_version_tuple >= (1, 14, 4)
"""Whether libhdf5 opens the sources of a virtual dataset with the file locking
flag of the file holding it. Older versions use the default flag instead, which
does not match a source this process already has open unlocked, so the read
returns the fill value of the dataset.
"""


@pytest.mark.parametrize("keep_open", [False, True])
def test_virtual_dataset_reaching_other_files(read_only_target, keep_open):
    """Verify a virtual dataset with sources this process cannot write is read
    through a copy, so its sources are opened read-only.
    """
    if keep_open and not _VIRTUAL_SOURCE_LOCKING:
        # The external links of the master keep the file the sources are in
        # open unlocked, which libhdf5 refuses to join for the sources.
        pytest.skip("libhdf5 locks the sources of a virtual dataset")

    master, _ = read_only_target
    with Hdf5File(
        master,
        mode="a",
        keep_open=keep_open,
        external_open_options={"mode": "r", "locking": False},
    ) as h5root:
        assert numpy.array_equal(h5root["/virtual/data"][()], [4, 5, 6])
        assert numpy.array_equal(h5root["/virtual/data"][()], [4, 5, 6])


def test_virtual_copies_are_removed(read_only_target):
    """Verify the copies of virtual datasets do not outlive the file."""
    master, _ = read_only_target
    tempfiles = _temporary_copies()

    h5root = Hdf5File(
        master,
        mode="a",
        keep_open=True,
        external_open_options={"mode": "r", "locking": False},
    )
    # Reading the dataset is what creates the copy.
    assert h5root["/virtual/data"].size == 3
    assert _temporary_copies() > tempfiles

    h5root.close()
    assert _temporary_copies() == tempfiles


def test_internal_virtual_dataset_is_not_copied(read_only_target):
    """Verify a virtual dataset with sources in the file itself is read through
    that file and not through a copy.
    """
    master, _ = read_only_target
    with Hdf5File(
        master, mode="a", external_open_options={"mode": "r", "locking": False}
    ) as h5root:
        assert numpy.array_equal(h5root["/internal/virtual/data"][()], [1, 2, 3])


def _temporary_copies() -> set:
    """The virtual dataset copies currently on disk."""
    return {
        name
        for name in os.listdir(tempfile.gettempdir())
        if name.startswith("vds") and name.endswith(".h5")
    }
