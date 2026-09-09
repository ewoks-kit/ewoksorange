import os
import stat

import h5py
import numpy
import pytest

from ...io.hdf5.links import LinkAwareFile
from ...io.hdf5.links import LinkAwareGroup
from ...io.hdf5.links import ReadOnlyLinksFile


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


def test_resolves_own_content(h5files):
    """Verify content of the file itself is reachable."""
    master, _ = h5files
    with LinkAwareFile(master, mode="r") as h5file:
        assert sorted(h5file) == ["linked", "own", "soft"]
        assert h5file["own"][0] == 9
        assert h5file["soft"][0] == 9
        assert h5file.filename == master


def test_resolves_external_link(h5files):
    """Verify an external link is followed into its own file."""
    master, target = h5files
    with LinkAwareFile(master, mode="r") as h5file:
        group = h5file["linked"]
        assert isinstance(group, LinkAwareGroup)
        assert group.attrs["NX_class"] == "NXentry"
        assert group.file is not h5file
        assert group.file.filename == target

        assert numpy.array_equal(h5file["linked/data"][()], [0, 1, 2, 3])
        assert numpy.array_equal(group["data"][()], [0, 1, 2, 3])


def test_external_access_options(h5files):
    """Verify external links use the options set for them."""
    master, _ = h5files
    with LinkAwareFile(master, mode="a") as h5file:
        h5file.set_external_access(mode="r")
        assert h5file.mode == "r+"
        assert h5file["linked"].file.mode == "r"


def test_read_access_falls_back_to_append(h5files):
    """Verify a file open for writing in this process stays readable."""
    master, _ = h5files
    with h5py.File(master, "a"):
        with ReadOnlyLinksFile(master) as h5file:
            assert h5file.mode == "r+"
            assert h5file["own"][0] == 9
            # The link target is untouched, so it is read-only.
            assert h5file["linked"].file.mode == "r"


def test_is_hashable(h5files):
    """Verify the wrapper can be kept in a set, like an h5py object."""
    master, _ = h5files
    with LinkAwareFile(master, mode="r") as h5file:
        assert {h5file, h5file["linked"]}


def test_read_access_refuses_other_modes(h5files):
    """Verify only reading and appending are allowed."""
    master, _ = h5files
    for mode in ("w", "r+", "w-"):
        with pytest.raises(ValueError):
            ReadOnlyLinksFile(master, mode=mode)


def test_read_access_for_a_file_we_will_write(h5files):
    """Verify append mode keeps external links read-only."""
    master, target = h5files
    with ReadOnlyLinksFile(master, mode="a") as h5file:
        assert h5file.mode == "r+"

        # Writing the file itself is what append mode is for.
        h5file["/own"][0] = 8
        assert h5file["/own"][0] == 8

        # The linked file is not written, and not locked either.
        assert h5file["linked"].file.mode == "r"
        assert h5file["linked"].file.filename == target
        with pytest.raises(OSError):
            h5file["linked/data"][0] = 99


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
    """Verify linked content is readable while the master is writable."""
    master, _ = read_only_target
    with LinkAwareFile(master, mode="a") as h5file:
        h5file.set_external_access(mode="r")

        assert "/internal/data" in h5file
        assert h5file["/internal/data"][()].tolist() == [1, 2, 3]
        assert "/external1/group/data" in h5file
        assert h5file["/external1/group/data"][()].tolist() == [4, 5, 6]
        assert "/external2/data" in h5file
        assert h5file["/external2/data"][()].tolist() == [4, 5, 6]

        assert "/internal/notexisting" not in h5file
        assert "/external1/group" in h5file
        assert "/external1/group/notexisting" not in h5file
        assert "/external2/notexisting" not in h5file


def test_write_through_links(read_only_target):
    """Verify only the master is writable when links are read-only."""
    master, _ = read_only_target
    with LinkAwareFile(master, mode="a") as h5file:
        h5file.set_external_access(mode="r")

        dataset = h5file["/internal/data"]
        dataset[0] = 99
        assert dataset[()].tolist() == [99, 2, 3]

        for path in ("/external1/group/data", "/external2/data"):
            dataset = h5file[path]
            with pytest.raises(OSError):
                dataset[0] = 99
            assert dataset[()].tolist() == [4, 5, 6]


def test_create_through_links(read_only_target):
    """Verify creating in a read-only linked file is refused."""
    master, target = read_only_target
    with LinkAwareFile(master, mode="a") as h5file:
        h5file["/internal/new"] = 10
        assert h5file["/internal/new"][()] == 10

        with pytest.raises(PermissionError):
            h5file["/external1/group/new"] = 20

    os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
    with LinkAwareFile(master, mode="a") as h5file:
        h5file["/external1/group/new"] = 30
        assert h5file["/external1/group/new"][()] == 30


def test_delete_through_links(read_only_target):
    """Verify deleting in a read-only linked file is refused."""
    master, target = read_only_target
    with LinkAwareFile(master, mode="a") as h5file:
        del h5file["/internal/data"]
        assert "/internal/data" not in h5file

        with pytest.raises(PermissionError):
            del h5file["/external1/group/data"]

        del h5file["/external2/data"]
        assert "/external2/data" not in h5file

    os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
    with LinkAwareFile(master, mode="a") as h5file:
        del h5file["/external1/group/data"]
        assert "/external1/group/data" not in h5file


@pytest.mark.parametrize(
    "h5path", ["/external1/group/data", "/external2/data", "/virtual/data"]
)
def test_read_target_while_writing_master(read_only_target, h5path):
    """Verify data of a file we cannot write is readable, whichever way it is
    reached, while the master is open for writing.
    """
    master, _ = read_only_target
    with ReadOnlyLinksFile(master, mode="a") as h5file:
        assert h5file.mode == "r+"
        assert numpy.array_equal(h5file[h5path][()], [4, 5, 6])


def test_internal_virtual_dataset_is_not_external(read_only_target):
    """Verify a virtual dataset with sources in the file itself is read through
    that file and not through a re-created one.
    """
    master, _ = read_only_target
    with ReadOnlyLinksFile(master, mode="a") as h5file:
        h5dataset = h5file["/internal/virtual/data"]
        assert h5dataset.file.filename == master
        assert numpy.array_equal(h5dataset[()], [1, 2, 3])


def test_virtual_source_file_follows_the_class(read_only_target):
    """Verify a re-created virtual dataset opens files the way its owner does."""
    master, _ = read_only_target
    with ReadOnlyLinksFile(master, mode="a") as h5file:
        h5file["/virtual/data"][()]
        virtual = h5file._virtual_source_files["/virtual/data"]
        assert isinstance(virtual, ReadOnlyLinksFile)
