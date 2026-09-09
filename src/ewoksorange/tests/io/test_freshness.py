"""What a reader sees while a writer changes the file."""

import h5py
import numpy
import pytest

from ...io.hdf5.base import Hdf5File
from ...io.hdf5.live import LiveFile
from ...io.hdf5.owned import OwnedFile
from ...io.hdf5.static import StaticFile

_REOPENING_CLASSES = [Hdf5File, LiveFile, OwnedFile]


@pytest.fixture
def h5file(tmp_path):
    """Create a file with a growable dataset in a group."""
    filename = str(tmp_path / "growing.h5")
    with h5py.File(filename, "w") as f:
        entry = f.create_group("entry")
        entry.attrs["NX_class"] = "NXentry"
        dataset = entry.create_dataset("data", data=numpy.arange(2.0), maxshape=(None,))
        dataset.attrs["units"] = "mm"
    return filename


@pytest.mark.parametrize("fileClass", _REOPENING_CLASSES)
def test_a_growing_dataset_is_followed(h5file, fileClass):
    """Verify the extent and the content of a dataset a writer appends to."""
    with fileClass(h5file) as h5root:
        dataset = h5root["entry/data"]
        assert dataset.shape == (2,)
        assert dataset.size == 2
        assert len(dataset) == 2
        assert dataset[()].tolist() == [0.0, 1.0]

        with h5py.File(h5file, "a") as f:
            f["entry/data"].resize((4,))
            f["entry/data"][2:] = [2.0, 3.0]

        assert dataset.shape == (4,)
        assert dataset.size == 4
        assert len(dataset) == 4
        assert dataset[()].tolist() == [0.0, 1.0, 2.0, 3.0]


@pytest.mark.parametrize("fileClass", _REOPENING_CLASSES)
def test_changed_attributes_are_followed(h5file, fileClass):
    """Verify attributes a writer adds or changes, at every level."""
    with fileClass(h5file) as h5root:
        group = h5root["entry"]
        dataset = group["data"]
        assert "creator" not in h5root.attrs
        assert group.attrs["NX_class"] == "NXentry"
        assert dataset.attrs["units"] == "mm"

        with h5py.File(h5file, "a") as f:
            f.attrs["creator"] = "test"
            f["entry"].attrs["default"] = "data"
            f["entry/data"].attrs["units"] = "um"

        assert h5root.attrs["creator"] == "test"
        assert group.attrs["default"] == "data"
        assert dataset.attrs["units"] == "um"


@pytest.mark.parametrize("fileClass", _REOPENING_CLASSES)
def test_new_children_need_a_refresh(h5file, fileClass):
    """Verify a group which was read stays as it was read until re-created."""
    h5root = fileClass(h5file)
    assert sorted(h5root["entry"]) == ["data"]

    with h5py.File(h5file, "a") as f:
        f["entry/added"] = [1]
        f["late"] = [1]

    # Read already, so it stays as it was read.
    assert sorted(h5root["entry"]) == ["data"]
    assert "late" not in h5root
    h5root.close()

    # Refreshing a viewer creates the object again, which reads it again.
    with fileClass(h5file) as h5root:
        assert sorted(h5root["entry"]) == ["added", "data"]
        assert "late" in h5root


def test_a_file_kept_open_is_a_snapshot(h5file):
    """Verify a file kept open shows what it held, and a new one what it holds."""
    h5root = StaticFile(h5file)
    assert h5root["entry/data"].shape == (2,)

    # Kept open read-only, so this process cannot write it meanwhile.
    h5root.close()
    with h5py.File(h5file, "a") as f:
        f["entry/data"].resize((4,))
        f["entry"].attrs["default"] = "data"

    with StaticFile(h5file) as h5root:
        assert h5root["entry/data"].shape == (4,)
        assert h5root["entry"].attrs["default"] == "data"
