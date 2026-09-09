"""Reading HDF5 files, whichever process is writing them.

Every file is exposed through the :mod:`silx.io.commonh5` API by
:class:`~ewoksorange.io.hdf5.base.Hdf5File`, with one module per access
regime on top of it: `static` for a file nobody writes, `live` for a file
another process may write and `owned` for a file this process writes. See the
HDF5 access explanation in the documentation.
"""
