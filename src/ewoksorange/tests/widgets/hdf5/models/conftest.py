import h5py
import pytest


@pytest.fixture
def h5file(tmp_path):
    """Create a minimal HDF5 file holding a single dataset."""
    filename = str(tmp_path / "data.h5")
    with h5py.File(filename, "w") as f:
        f["existing"] = 42
    return filename
