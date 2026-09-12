import os
import posixpath
import tempfile
from collections import abc
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Union

import h5py
from silx.io import h5py_utils
from silx.io.utils import H5Type

from .access import open_for_reading


class LinkAwareGroup(abc.MutableMapping):
    """Wrapper around an HDF5 group which delegates path resolution to its file."""

    h5_class = H5Type.GROUP

    def __init__(self, h5group: h5py.Group, h5file: "LinkAwareFile") -> None:
        self._h5group = h5group
        self._h5file = h5file

    def __getitem__(self, name: str) -> Union[h5py.Dataset, "LinkAwareGroup"]:
        return self._h5file._resolve(self._h5group, name)

    def __setitem__(self, name: str, value: Any) -> None:
        parent_name, _, child_name = name.rpartition("/")
        parent = self._h5file._resolve(self._h5group, parent_name)
        parent._h5group[child_name] = value

    def __delitem__(self, name: str) -> None:
        parent_name, _, child_name = name.rpartition("/")
        parent = self._h5file._resolve(self._h5group, parent_name)
        del parent._h5group[child_name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._h5group)

    def __len__(self) -> int:
        return len(self._h5group)

    def __repr__(self) -> str:
        return f'<{type(self).__name__} "{self.name}">'

    # A mapping is unhashable by default, but h5py objects are hashable and
    # callers keep them in sets and dictionaries.
    __hash__ = object.__hash__

    @property
    def name(self) -> str:
        return self._h5group.name

    @property
    def file(self) -> "LinkAwareFile":
        return self._h5file

    @property
    def parent(self) -> "LinkAwareGroup":
        return LinkAwareGroup(self._h5group.parent, self._h5file)

    @property
    def attrs(self) -> h5py.AttributeManager:
        return self._h5group.attrs

    def get(
        self,
        name: str,
        default: Any = None,
        getclass: bool = False,
        getlink: bool = False,
    ) -> Any:
        if getclass or getlink:
            return self._h5group.get(
                name, default=default, getclass=getclass, getlink=getlink
            )
        if name in self._h5group:
            return self[name]
        return default


class LinkAwareFile(LinkAwareGroup):
    """HDF5 file which opens external links with their own options.

    Unlike :mod:`h5py`, which follows an external link with the options of the
    file holding it, the options set by :meth:`set_external_access` are used.
    """

    h5_class = H5Type.FILE

    def __init__(
        self, filename: str, *, _external: bool = False, **open_options
    ) -> None:
        self._external_open_options: Dict[str, Any] = dict(open_options)
        if _external:
            self._h5native = self._open_external_file(filename, **open_options)
        else:
            self._h5native = self._open_native_file(filename, **open_options)
        self._external_files: Dict[str, LinkAwareFile] = {}
        self._virtual_source_files: Dict[str, "LinkAwareFile"] = {}
        self._virtual_dataset_name: Optional[str] = None
        self._virtual_prefix: Optional[str] = None
        self._cached_virtual_dataset: Optional[h5py.Dataset] = None
        self._filename_to_remove: Optional[str] = None
        super().__init__(self._h5native, self)

    @classmethod
    def _from_virtual_dataset(
        cls, h5dataset: h5py.Dataset, **open_options
    ) -> "LinkAwareFile":
        """Re-create `h5dataset` in a temporary file: the same virtual mapping,
        HDF5 path and attributes, so no data is copied. The file is removed while
        open when the platform allows it and when closed otherwise.
        """
        handle, filename = tempfile.mkstemp(prefix="vds", suffix=".h5")
        os.close(handle)
        try:
            with h5py.File(filename, "w") as h5file:
                parent = h5file.require_group(posixpath.dirname(h5dataset.name))
                h5id = h5py.h5d.create(
                    parent.id,
                    posixpath.basename(h5dataset.name).encode(),
                    h5dataset.id.get_type(),
                    h5dataset.id.get_space(),
                    dcpl=h5dataset.id.get_create_plist(),
                )
                h5py.Dataset(h5id).attrs.update(h5dataset.attrs)
            virtual = cls(filename, _external=True, **open_options)
        except BaseException:
            os.remove(filename)
            raise

        virtual._virtual_dataset_name = h5dataset.name
        # Relative source paths resolve against the file the dataset belongs to,
        # absolute ones are unaffected by the prefix
        virtual._virtual_prefix = os.path.dirname(
            os.path.abspath(h5dataset.file.filename)
        )
        virtual._filename_to_remove = filename
        virtual._remove_file()
        return virtual

    def _virtual_dataset(self) -> h5py.Dataset:
        """The virtual dataset this file was created for."""
        if self._cached_virtual_dataset is None:
            dapl = h5py.h5p.create(h5py.h5p.DATASET_ACCESS)
            dapl.set_virtual_prefix(self._virtual_prefix.encode())
            self._cached_virtual_dataset = h5py.Dataset(
                h5py.h5d.open(
                    self._h5native.id, self._virtual_dataset_name.encode(), dapl=dapl
                )
            )
        return self._cached_virtual_dataset

    def _remove_file(self) -> None:
        if self._filename_to_remove is None:
            return
        try:
            os.remove(self._filename_to_remove)  # the open handle keeps working
        except OSError:
            return  # Windows: remove when closing
        self._filename_to_remove = None

    def _open_native_file(self, filename: str, **open_options) -> h5py.File:
        """Open the file this instance gives access to."""
        return h5py_utils.File(filename, **open_options)

    def _open_external_file(self, filename: str, **open_options) -> h5py.File:
        """Open a file this instance gets data from, which is in its own regime.
        The same for an external link and for a virtual dataset source.
        """
        return h5py_utils.File(filename, **open_options)

    def __enter__(self) -> "LinkAwareFile":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @property
    def filename(self) -> str:
        return self._h5native.filename

    @property
    def mode(self) -> str:
        return self._h5native.mode

    @property
    def parent(self) -> "LinkAwareFile":
        return self

    def set_external_access(self, **open_options) -> None:
        """Set the options used for the files external links point to."""
        self._external_open_options.update(open_options)

    def close(self) -> None:
        self._cached_virtual_dataset = None
        for h5files in (self._external_files, self._virtual_source_files):
            for h5file in list(h5files.values()):
                h5file.close()
            h5files.clear()
        if self._h5native is not None:
            try:
                self._h5native.close()
            finally:
                self._h5native = None
        self._remove_file()

    def _open_external(self, filename: str, h5file: h5py.File) -> "LinkAwareFile":
        if not os.path.isabs(filename):
            filename = os.path.join(os.path.dirname(h5file.filename), filename)
        filename = os.path.realpath(filename)

        external = self._external_files.get(filename)
        if external is None:
            external = type(self)(
                filename, _external=True, **self._external_open_options
            )
            self._external_files[filename] = external
        return external

    def _open_virtual_source(self, h5dataset: h5py.Dataset) -> "LinkAwareFile":
        name = h5dataset.name
        virtual = self._virtual_source_files.get(name)
        if virtual is None:
            virtual = type(self)._from_virtual_dataset(
                h5dataset, **self._external_open_options
            )
            self._virtual_source_files[name] = virtual
        return virtual

    def _has_external_virtual_sources(self, h5dataset: h5py.Dataset) -> bool:
        """Whether `h5dataset` is a virtual dataset with sources in other files."""
        if not h5dataset.is_virtual:
            return False
        # HDF5 opens the sources with the access mode of the file itself
        if _access_mode(self._external_open_options) == self._h5native.mode:
            return False
        return any(
            _is_external_source(h5dataset, source)
            for source in h5dataset.virtual_sources()
        )

    def _resolve(
        self, h5group: h5py.Group, name: str
    ) -> Union[h5py.Dataset, LinkAwareGroup]:
        """Return the object at `name`, following links explicitly."""
        h5current = h5group.file if name.startswith("/") else h5group
        current = self
        parts = [part for part in name.split("/") if part]

        index = 0
        while index < len(parts):
            link = h5current.get(parts[index], default=None, getlink=True)

            if isinstance(link, h5py.ExternalLink):
                external = self._open_external(link.filename, h5current.file)
                parts = _split_path(link.path) + parts[index + 1 :]
                h5current = external._h5native
                current = external
                index = 0
                continue

            if isinstance(link, h5py.SoftLink):
                parts = _split_path(link.path) + parts[index + 1 :]
                if link.path.startswith("/"):
                    h5current = h5current.file
                index = 0
                continue

            h5object = h5current[parts[index]]
            index += 1
            if index < len(parts):
                if not isinstance(h5object, h5py.Group):
                    raise KeyError(
                        f"Cannot descend into '{h5object.name}' while resolving {name!r}"
                    )
            h5current = h5object

        if isinstance(h5current, h5py.Group):
            return LinkAwareGroup(h5current, current)
        if current._has_external_virtual_sources(h5current):
            return current._open_virtual_source(h5current)._virtual_dataset()
        return h5current


class ReadOnlyLinksFile(LinkAwareFile):
    """An HDF5 file whose external links are always read read-only and unlocked.

    The file itself is opened in the regime it is in: joined when the current
    process already has it open, read-only and unlocked otherwise. Pass `mode`
    "a" when the current process will open it for writing later. Whatever that
    regime, the files its links point at are only read, so raw data the current
    process does not write stays readable. See
    :mod:`ewoksorange.io.hdf5.access`.
    """

    def __init__(self, filename: str, mode: Optional[str] = None, **open_options):
        if mode not in (None, "r", "a"):
            raise ValueError("must be opened read-only or in append mode")
        self._requested_mode = mode
        super().__init__(filename, **open_options)
        # Every linked file resolves its own mode the same way: joined when the
        # current process already has it open, read-only and unlocked
        # otherwise. Forcing read-only here would clash with the locking flags
        # of a linked file the current process has open for writing.
        self._external_open_options = {}

    def _open_native_file(self, filename: str, **open_options) -> h5py.File:
        if self._requested_mode == "a":
            return h5py_utils.File(filename, mode="a", **open_options)
        return open_for_reading(filename, **open_options)

    def _open_external_file(self, filename: str, **open_options) -> h5py.File:
        return open_for_reading(filename, **open_options)


def _access_mode(open_options: Dict[str, Any]) -> str:
    """The `h5py.File.mode` of a file opened with these options."""
    mode = open_options.get("mode")
    return "r" if mode is None or mode == "r" else "r+"


def _is_external_source(h5dataset: h5py.Dataset, source) -> bool:
    """Whether the virtual source is in another file than `h5dataset`."""
    filename = source.file_name
    if filename == ".":
        return False
    own = os.path.abspath(h5dataset.file.filename)
    if not os.path.isabs(filename):
        filename = os.path.join(os.path.dirname(own), filename)
    return os.path.realpath(filename) != os.path.realpath(own)


def _split_path(path: str) -> list:
    return [part for part in path.split("/") if part]
