import h5py
import numpy
import pytest

from ...io.hdf5.links import LinkAwareFile
from ...io.hdf5.live import LiveFile
from ...io.hdf5.utils import is_dataset
from ...io.hdf5.utils import is_externallink
from ...io.hdf5.utils import is_file
from ...io.hdf5.utils import is_group
from ...io.hdf5.utils import is_softlink
from ...io.hdf5.utils import split_h5data_path


@pytest.fixture
def h5file(tmp_path):
    """Create a file with a group, a dataset and both link kinds."""
    target = str(tmp_path / "target.h5")
    with h5py.File(target, "w") as f:
        f["entry/data"] = numpy.arange(3)

    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["entry/data"] = numpy.arange(3)
        f["soft"] = h5py.SoftLink("/entry/data")
        f["external"] = h5py.ExternalLink("target.h5", "/entry")
    return filename


def test_split_h5data_path():
    """Verify a path is split into its names."""
    assert split_h5data_path("/entry/data") == ["entry", "data"]
    assert split_h5data_path("entry/data/") == ["entry", "data"]
    assert split_h5data_path("//entry//data//") == ["entry", "data"]
    assert split_h5data_path("/") == []
    assert split_h5data_path("") == []


@pytest.mark.parametrize("proxy", ["h5py", "external", "reopening"])
def test_predicates(h5file, proxy):
    """Verify the predicates hold for every kind of HDF5 object."""
    if proxy == "h5py":
        h5root = h5py.File(h5file, "r")
    elif proxy == "external":
        h5root = LinkAwareFile(h5file, mode="r")
    else:
        h5root = LiveFile(h5file)

    try:
        assert is_file(h5root)
        # A file is a group.
        assert is_group(h5root)
        assert not is_dataset(h5root)

        group = h5root["entry"]
        assert is_group(group)
        assert not is_file(group)
        assert not is_dataset(group)

        dataset = h5root["entry/data"]
        assert is_dataset(dataset)
        assert not is_group(dataset)
        assert not is_file(dataset)
    finally:
        h5root.close()


def test_link_predicates(h5file):
    """Verify links are recognised."""
    with h5py.File(h5file, "r") as h5root:
        assert is_softlink(h5root.get("soft", getlink=True))
        assert is_externallink(h5root.get("external", getlink=True))
        assert not is_softlink(h5root.get("entry", getlink=True))
        assert not is_externallink(h5root.get("soft", getlink=True))
