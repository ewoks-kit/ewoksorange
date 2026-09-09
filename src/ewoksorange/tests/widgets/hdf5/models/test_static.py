import sys

import pytest

from .....gui.widgets.hdf5.model.static import StaticFileTreeModel
from .utils import open_from_other_process
from .utils import opened_files
from .utils import tree_model


def test_default_open_options(ewoksorange_qtapp, h5file):
    """Verify StaticFileTreeModel opens files read-only and unlocked by default."""
    with tree_model() as model:
        assert model.openOptions == {"mode": "r", "locking": False}

        model.insertFile(h5file)
        (h5,) = opened_files(model)
        assert h5.mode == "r"
        assert h5["existing"][()] == 42

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OPENED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OPENED"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
def test_configurable_mode_and_locking(ewoksorange_qtapp, h5file):
    """Verify configured modes and locked states match expectations."""

    # #########################
    # Read-Only Mode
    # #########################
    with tree_model(StaticFileTreeModel, mode="r", locking=False) as model:
        model.insertFile(h5file)
        (h5,) = opened_files(model)
        assert h5.mode == "r"
        assert h5["existing"][()] == 42

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OPENED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OPENED"

    with tree_model(StaticFileTreeModel, mode="r", locking=True) as model:
        model.insertFile(h5file)
        (h5,) = opened_files(model)
        assert h5.mode == "r"
        assert h5["existing"][()] == 42

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OSError:LOCKED"

    # #########################
    # Append Mode
    # #########################
    with tree_model(StaticFileTreeModel, mode="a", locking=False) as model:
        model.insertFile(h5file)
        (h5,) = opened_files(model)
        assert h5.mode == "r+"
        assert h5["existing"][()] == 42

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OPENED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OPENED"

    with tree_model(StaticFileTreeModel, mode="a", locking=True) as model:
        model.insertFile(h5file)
        (h5,) = opened_files(model)
        assert h5.mode == "r+"
        assert h5["existing"][()] == 42

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OSError:LOCKED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OSError:LOCKED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OSError:LOCKED"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
def test_configurable_mode_and_locking_windows(ewoksorange_qtapp, h5file):
    """Verify configured modes and locked states match expectations."""

    # #########################
    # Read-Only Mode
    # #########################
    with tree_model(StaticFileTreeModel, mode="r", locking=False) as model:
        model.insertFile(h5file)
        (h5,) = opened_files(model)
        assert h5.mode == "r"
        assert h5["existing"][()] == 42

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OPENED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OPENED"

    with tree_model(StaticFileTreeModel, mode="r", locking=True) as model:
        model.insertFile(h5file)
        (h5,) = opened_files(model)
        assert h5.mode == "r"
        assert h5["existing"][()] == 42

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.not_locking == "OSError:LOCKED"
        assert external_append.default == "OSError:LOCKED"

    # #########################
    # Append Mode
    # #########################
    with tree_model(StaticFileTreeModel, mode="a", locking=False) as model:
        model.insertFile(h5file)
        (h5,) = opened_files(model)
        assert h5.mode == "r+"
        assert h5["existing"][()] == 42

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OPENED"
        assert external_read.not_locking == "OPENED"
        assert external_read.default == "OPENED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OPENED"
        assert external_append.not_locking == "OPENED"
        assert external_append.default == "OPENED"

    with tree_model(StaticFileTreeModel, mode="a", locking=True) as model:
        model.insertFile(h5file)
        (h5,) = opened_files(model)
        assert h5.mode == "r+"
        assert h5["existing"][()] == 42

        external_read = open_from_other_process(h5file, mode="r")
        assert external_read.locking == "OSError:LOCKED"
        assert external_read.not_locking == "OSError:LOCKED"
        assert external_read.default == "OSError:LOCKED"

        external_append = open_from_other_process(h5file, mode="a")
        assert external_append.locking == "OSError:LOCKED"
        assert external_append.not_locking == "OSError:LOCKED"
        assert external_append.default == "OSError:LOCKED"
