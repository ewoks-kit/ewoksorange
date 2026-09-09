"""Reading an HDF5 file through the :mod:`silx.io.commonh5` API."""

import logging
import os
import posixpath
import tempfile
import traceback
from contextlib import ExitStack
from contextlib import contextmanager
from functools import cached_property
from types import MappingProxyType
from typing import Any
from typing import ContextManager
from typing import Dict
from typing import Generator
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

import h5py
from silx.io import commonh5
from silx.io import h5py_utils

from .access import external_link_filename
from .utils import is_group

_logger = logging.getLogger(__name__)

_MAX_LINK_DEPTH = 16
"""Depth limit which stops following links in a circle."""


class Hdf5Attributes:
    """Attributes read from the file on every access.

    A writer can add or change an attribute at any time, so a copy taken when
    the node was created would go stale without anything saying so.
    """

    _source: "_Source"

    @property
    def attrs(self) -> Mapping[str, Any]:
        with self._source.open() as h5object:
            return MappingProxyType(dict(h5object.attrs))


class Hdf5File(Hdf5Attributes, commonh5.File):
    """Read-only view of an HDF5 file, exposing the :mod:`silx.io.commonh5` API.

    The file is opened by :meth:`open_h5_file`, and the files its external
    links point at by :meth:`open_external_h5_file`, which is what lets each of
    them be opened in its own :term:`access regime`. `external_open_options`
    are the options of those linked files and default to `open_options`.

    `keep_open` keeps every file open until :meth:`close`. Leave it off for a
    file which is being written: a handle kept open never sees writes which
    land after it was opened, and it stops this process from writing that file.

    What a writer changes while the file is being read shows up as follows:
    the content, extent and attributes of a dataset, and the attributes of a
    group, are read from the file on every access, so they are never stale;
    the children of a group are read once, when they are first asked for, so a
    group which has not been looked at yet shows what the writer has added
    since, and one which has shows what was there when it was read. Creating
    this object again reads everything again, which is what refreshing a viewer
    does.

    Reading on every access is what costs an open per access when `keep_open`
    is off, which is the price of never showing something the file no longer
    holds.
    """

    def __init__(
        self,
        name: str,
        keep_open: bool = False,
        external_open_options: Optional[Mapping[str, Any]] = None,
        **open_options,
    ) -> None:
        self._open_options: Dict[str, Any] = dict(open_options)
        self._external_open_options: Dict[str, Any] = (
            dict(open_options)
            if external_open_options is None
            else dict(external_open_options)
        )
        self._keep_open = keep_open
        self._open_files: Dict[str, h5py.File] = {}
        self._virtual_copies: Dict[Tuple[str, str], str] = {}
        self._exit_stack = ExitStack()
        self._source = _Source(self, name, "/", self._open_options, external=False)
        self.__is_initialized = False
        # Opened once here so that a file which cannot be read fails to be
        # created, instead of failing later on a read of its content.
        with self._source.open():
            pass
        super().__init__(name=name, mode="r")

    def open_h5_file(self, filename: str, **open_options) -> ContextManager[h5py.File]:
        """Return a context manager giving access to the file itself."""
        return h5py_utils.File(filename, **open_options)

    def open_external_h5_file(
        self, filename: str, **open_options
    ) -> ContextManager[h5py.File]:
        """Return a context manager giving access to a file an external link
        points at.
        """
        return self.open_h5_file(filename, **open_options)

    def close(self) -> None:
        self._open_files.clear()
        self._exit_stack.close()
        for filename in self._virtual_copies.values():
            _remove_file(filename)
        self._virtual_copies.clear()

    def _get_items(self) -> Dict[str, commonh5.Node]:
        # Same lazy loading as commonh5.LazyLoadableGroup, which File cannot
        # inherit from: the children are read when they are first asked for.
        if not self.__is_initialized:
            self.__is_initialized = True
            with self._source.open() as h5group:
                _add_nodes(self, h5group, self._source)
        return super()._get_items()

    @contextmanager
    def _open_h5_file(
        self, filename: str, open_options: Mapping[str, Any], external: bool
    ) -> Generator[h5py.File, None, None]:
        open_file = self.open_external_h5_file if external else self.open_h5_file
        if not self._keep_open:
            with open_file(filename, **open_options) as h5file:
                yield h5file
            return

        key = os.path.realpath(filename)
        h5file = self._open_files.get(key)
        if h5file is None:
            h5file = self._exit_stack.enter_context(open_file(filename, **open_options))
            self._open_files[key] = h5file
        yield h5file

    @contextmanager
    def _open_virtual_copy(
        self, h5dataset: h5py.Dataset
    ) -> Generator[h5py.Dataset, None, None]:
        """Yield a copy of `h5dataset` opened like a linked file."""
        key = (os.path.realpath(h5dataset.file.filename), h5dataset.name)
        filename = self._virtual_copies.get(key)
        temporary = filename is None
        if temporary:
            filename = _create_virtual_copy(h5dataset)
            if self._keep_open:
                self._virtual_copies[key] = filename
                temporary = False
        try:
            with self._open_h5_file(
                filename, self._external_open_options, external=True
            ) as h5file:
                yield _open_virtual_copy(h5file, h5dataset)
        finally:
            if temporary:
                _remove_file(filename)

    def _needs_virtual_copy(self, h5file: h5py.File) -> bool:
        """Whether a virtual dataset of `h5file` with sources in other files
        must be read through a copy.

        HDF5 opens those sources with the options of `h5file`, which is the
        wrong access regime for them whenever a linked file is opened
        differently.
        """
        return _access_mode(self._external_open_options) != h5file.mode


class Hdf5Group(Hdf5Attributes, commonh5.LazyLoadableGroup):
    """Read-only view of an HDF5 group.

    Its children are read when they are first asked for, not when it is
    created, so a group which is never looked at is never read and a group
    looked at later shows what the file held at that moment.
    """

    def __init__(self, name: str, parent: commonh5.Group, source: "_Source") -> None:
        super().__init__(name, parent=parent)
        self._source = source

    def _create_child(self) -> None:
        with self._source.open() as h5group:
            _add_nodes(self, h5group, self._source)


class Hdf5Dataset(Hdf5Attributes, commonh5.Dataset):
    """Read-only view of an HDF5 dataset, read on every access."""

    def __init__(self, name: str, parent: commonh5.Group, source: "_Source") -> None:
        super().__init__(name, None, parent=parent, attrs=None)
        self._source = source

    @contextmanager
    def _open_h5_dataset(self) -> Generator[h5py.Dataset, None, None]:
        with self._source.open() as h5dataset:
            yield h5dataset

    def _get_h5attribute(self, attr: str) -> Any:
        with self._open_h5_dataset() as h5dataset:
            return getattr(h5dataset, attr)

    # Read on every access: a writer can grow a dataset it is still filling.
    shape = property(lambda self: self._get_h5attribute("shape"))
    size = property(lambda self: self._get_h5attribute("size"))

    # Fixed when the dataset is created, so read once.
    dtype = cached_property(lambda self: self._get_h5attribute("dtype"))
    ndim = cached_property(lambda self: self._get_h5attribute("ndim"))
    compression = cached_property(lambda self: self._get_h5attribute("compression"))
    compression_opts = cached_property(
        lambda self: self._get_h5attribute("compression_opts")
    )
    chunks = cached_property(lambda self: self._get_h5attribute("chunks"))
    is_virtual = cached_property(lambda self: self._get_h5attribute("is_virtual"))
    virtual_sources = cached_property(
        lambda self: self._get_h5attribute("virtual_sources")
    )
    external = cached_property(lambda self: self._get_h5attribute("external"))

    def __len__(self) -> int:
        with self._open_h5_dataset() as h5dataset:
            return len(h5dataset)

    def __getitem__(self, item) -> Any:
        with self._open_h5_dataset() as h5dataset:
            return h5dataset[item]

    def __iter__(self) -> Iterator:
        return self[()].__iter__()

    def __bool__(self) -> bool:
        with self._open_h5_dataset() as h5dataset:
            return bool(h5dataset)

    def __getattr__(self, item: str) -> Any:
        """Proxy to the underlying numpy array, for `numpy.array(dataset)`."""
        data = self[()]
        if hasattr(data, item):
            return getattr(data, item)
        raise AttributeError(f"Dataset has no attribute {item}")

    @property
    def value(self):
        raise NotImplementedError  # h5py v2 property, should not be used

    def _get_data(self) -> Any:
        # Every base class method calling this is overridden.
        _logger.warning(
            "Hdf5Dataset._get_data should not be called\nStack trace:\n%s",
            "".join(traceback.format_stack()),
        )
        return self[()]


class _Source:
    """The HDF5 file and path a node reads from."""

    def __init__(
        self,
        root: Hdf5File,
        filename: str,
        path: str,
        open_options: Mapping[str, Any],
        external: bool,
    ) -> None:
        self.root = root
        self.filename = filename
        self.path = path
        self.open_options = open_options
        self.external = external

    def child(self, name: str) -> "_Source":
        path = f"{self.path.rstrip('/')}/{name}"
        return _Source(self.root, self.filename, path, self.open_options, self.external)

    def link(self, link: h5py.ExternalLink, h5file: h5py.File) -> "_Source":
        return _Source(
            self.root,
            external_link_filename(link, h5file),
            link.path,
            self.root._external_open_options,
            external=True,
        )

    def at_root(self) -> "_Source":
        return _Source(self.root, self.filename, "/", self.open_options, self.external)

    def virtual(self) -> "_VirtualSource":
        return _VirtualSource(
            self.root, self.filename, self.path, self.open_options, self.external
        )

    @contextmanager
    def open(self) -> Generator[Union[h5py.Group, h5py.Dataset], None, None]:
        with self.root._open_h5_file(
            self.filename, self.open_options, self.external
        ) as h5file:
            yield h5file[self.path]


class _VirtualSource(_Source):
    """A virtual dataset whose sources are in files of another regime."""

    @contextmanager
    def open(self) -> Generator[h5py.Dataset, None, None]:
        with self.root._open_h5_file(
            self.filename, self.open_options, self.external
        ) as h5file:
            with self.root._open_virtual_copy(h5file[self.path]) as h5dataset:
                yield h5dataset


def _add_nodes(
    group: Union[Hdf5File, Hdf5Group],
    h5group: Union[h5py.File, h5py.Group],
    source: _Source,
) -> None:
    for name in h5group:
        try:
            with _open_child(source, h5group, name) as (child_source, h5child):
                _add_node(group, name, child_source, h5child)
        except (OSError, KeyError, RuntimeError):
            # A link can be broken for any reason; skipping it keeps the rest
            # of the file readable.
            _logger.warning(
                "Skipping '%s/%s'", h5group.name.rstrip("/"), name, exc_info=True
            )


def _add_node(
    group: Union[Hdf5File, Hdf5Group],
    name: str,
    source: _Source,
    h5object: Union[h5py.Group, h5py.Dataset],
) -> None:
    if is_group(h5object):
        group.add_node(Hdf5Group(name, group, source))
        return
    if _has_external_sources(h5object) and source.root._needs_virtual_copy(
        h5object.file
    ):
        source = source.virtual()
    group.add_node(Hdf5Dataset(name, group, source))


@contextmanager
def _open_child(
    source: _Source,
    h5group: Union[h5py.File, h5py.Group],
    name: str,
    depth: int = 0,
) -> Generator[Tuple[_Source, Union[h5py.Group, h5py.Dataset]], None, None]:
    """Yield the source and the open object `name` leads to.

    Links are followed here instead of by h5py, which opens the file a link
    leads into with the options of the file holding the link, so a soft link
    whose target is an external link ends up opening that file in the wrong
    access regime.
    """
    if depth > _MAX_LINK_DEPTH:
        raise KeyError(f"Too many links to follow for '{name}'")

    link = h5group.get(name, default=None, getlink=True)
    if link is None:
        raise KeyError(f"'{name}' does not exist")

    if isinstance(link, h5py.ExternalLink):
        child_source = source.link(link, h5group.file)
        with child_source.open() as h5child:
            yield child_source, h5child
        return

    if isinstance(link, h5py.SoftLink):
        if link.path.startswith("/"):
            target_source, h5target = source.at_root(), h5group.file
        else:
            target_source, h5target = source, h5group
        names = [part for part in link.path.split("/") if part]
        with _open_path(target_source, h5target, names, depth + 1) as resolved:
            yield resolved
        return

    yield source.child(name), h5group[name]


@contextmanager
def _open_path(
    source: _Source,
    h5group: Union[h5py.File, h5py.Group],
    names: Sequence[str],
    depth: int,
) -> Generator[Tuple[_Source, Union[h5py.Group, h5py.Dataset]], None, None]:
    """Yield the source and the open object `names` leads to, one name at a
    time so a link on the way is followed by :func:`_open_child`.
    """
    if not names:
        yield source, h5group
        return
    with _open_child(source, h5group, names[0], depth) as (child_source, h5child):
        with _open_path(child_source, h5child, names[1:], depth) as resolved:
            yield resolved


def _has_external_sources(h5dataset: h5py.Dataset) -> bool:
    """Whether `h5dataset` is a virtual dataset with sources in other files."""
    if not h5dataset.is_virtual:
        return False
    return any(
        _is_external_source(h5dataset, source) for source in h5dataset.virtual_sources()
    )


def _is_external_source(h5dataset: h5py.Dataset, source) -> bool:
    """Whether the virtual source is in another file than `h5dataset`."""
    filename = source.file_name
    if filename == ".":
        return False
    own = os.path.abspath(h5dataset.file.filename)
    if not os.path.isabs(filename):
        filename = os.path.join(os.path.dirname(own), filename)
    return os.path.realpath(filename) != os.path.realpath(own)


def _create_virtual_copy(h5dataset: h5py.Dataset) -> str:
    """Re-create `h5dataset` in a temporary file: the same virtual mapping,
    HDF5 path and attributes, so no data is copied.
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
    except BaseException:
        _remove_file(filename)
        raise
    return filename


def _open_virtual_copy(h5file: h5py.File, h5dataset: h5py.Dataset) -> h5py.Dataset:
    """Open the copy of `h5dataset` held by `h5file`.

    Relative source names resolve against the directory of the file the
    original dataset belongs to, absolute ones are unaffected by the prefix.
    """
    prefix = os.path.dirname(os.path.abspath(h5dataset.file.filename))
    dapl = h5py.h5p.create(h5py.h5p.DATASET_ACCESS)
    dapl.set_virtual_prefix(prefix.encode())
    return h5py.Dataset(h5py.h5d.open(h5file.id, h5dataset.name.encode(), dapl=dapl))


def _remove_file(filename: str) -> None:
    try:
        os.remove(filename)
    except OSError:
        # Windows refuses to remove a file which is still open.
        _logger.debug("Cannot remove '%s'", filename, exc_info=True)


def _access_mode(open_options: Mapping[str, Any]) -> str:
    """The `h5py.File.mode` of a file opened with these options."""
    mode = open_options.get("mode")
    return "r" if mode is None or mode == "r" else "r+"
