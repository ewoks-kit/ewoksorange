"""Reading a file another process may be writing."""

import logging
import traceback
from contextlib import contextmanager
from functools import cached_property
from types import MappingProxyType
from typing import Any
from typing import Generator
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Union

import h5py
from silx.io import commonh5
from silx.io import h5py_utils

from .access import external_link_filename
from .utils import is_group

_logger = logging.getLogger(__name__)


class LiveFile(commonh5.File):
    """An HDF5 file which is only open while it is being read.

    Use it for a file another process may be writing. Opening it read-only and
    unlocked, which is what the open options must say, is what leaves that
    writer unblocked. Closing it between reads is what lets a later read see
    what the writer has written since, because a handle kept open never sees
    anything added after it was opened.

    Without SWMR a writer only makes its writes visible to other processes when
    it closes the file, so a read shows the state the writer last left behind
    rather than what it is writing now.

    The structure is read once, the content on every access, so another process
    can have the file open for writing the whole time it is being read.

    `external_open_options` are the options used for the files external links
    point to. They default to `open_options`.
    """

    def __init__(
        self,
        name: str,
        external_open_options: Optional[Mapping[str, Any]] = None,
        **open_options,
    ):
        self._open_options = open_options
        self._external_open_options = (
            dict(open_options)
            if external_open_options is None
            else dict(external_open_options)
        )
        source = _Source(self, name, "/", open_options)
        # Not self._h5open: the file name is only known after super().__init__.
        with source.open() as h5group:
            super().__init__(name=name, mode="r", attrs=dict(h5group.attrs))
            self._source = source
            _add_nodes(self, h5group, source)

    def open_h5_file(self, filename: str, **open_options):
        """Return a context manager giving access to an HDF5 file."""
        return h5py_utils.File(filename, **open_options)

    @contextmanager
    def _h5open(self) -> Generator[h5py.File, None, None]:
        with self.open_h5_file(self.filename, **self._open_options) as h5file:
            yield h5file


class LiveGroup(commonh5.Group):
    """Proxy to an HDF5 group which is only open while it is read."""

    def __init__(
        self,
        name: str,
        parent: commonh5.Group,
        source: "_Source",
        h5group: Optional[h5py.Group] = None,
    ):
        if h5group is not None:
            super().__init__(name, parent=parent, attrs=dict(h5group.attrs))
            self._source = source
            _add_nodes(self, h5group, source)
            return
        with source.open() as h5group:
            super().__init__(name, parent=parent, attrs=dict(h5group.attrs))
            self._source = source
            _add_nodes(self, h5group, source)


class LiveDataset(commonh5.Dataset):
    """Proxy to an HDF5 dataset which is only open while it is read."""

    def __init__(self, name: str, parent: commonh5.Group, source: "_Source"):
        super().__init__(name, None, parent=parent, attrs=None)
        self._source = source

    @contextmanager
    def _open_h5_dataset(self) -> Generator[h5py.Dataset, None, None]:
        with self._source.open() as h5dataset:
            yield h5dataset

    def _get_h5attribute(self, attr: str) -> Any:
        with self._open_h5_dataset() as h5dataset:
            return getattr(h5dataset, attr)

    dtype = cached_property(lambda self: self._get_h5attribute("dtype"))
    shape = cached_property(lambda self: self._get_h5attribute("shape"))
    size = cached_property(lambda self: self._get_h5attribute("size"))
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

    @cached_property
    def attrs(self) -> Mapping[str, Any]:
        with self._open_h5_dataset() as h5dataset:
            return MappingProxyType(dict(h5dataset.attrs))

    @property
    def value(self):
        raise NotImplementedError  # h5py v2 property, should not be used

    def _get_data(self) -> Any:
        # Every base class method calling this is overridden.
        _logger.warning(
            "LiveDataset._get_data should not be called\nStack trace:\n%s",
            "".join(traceback.format_stack()),
        )
        return self[()]


class _Source:
    """The HDF5 file and path a proxy node reads from."""

    def __init__(
        self,
        root: LiveFile,
        filename: str,
        path: str,
        open_options: Mapping[str, Any],
    ) -> None:
        self.root = root
        self.filename = filename
        self.path = path
        self.open_options = open_options

    def child(self, name: str) -> "_Source":
        path = f"{self.path.rstrip('/')}/{name}"
        return _Source(self.root, self.filename, path, self.open_options)

    def external(self, link: h5py.ExternalLink, h5file: h5py.File) -> "_Source":
        return _Source(
            self.root,
            external_link_filename(link, h5file),
            link.path,
            self.root._external_open_options,
        )

    @contextmanager
    def open(self) -> Generator[Union[h5py.Group, h5py.Dataset], None, None]:
        with self.root.open_h5_file(self.filename, **self.open_options) as h5file:
            yield h5file[self.path]


def _add_nodes(
    group: Union[LiveFile, LiveGroup],
    h5group: Union[h5py.File, h5py.Group],
    source: _Source,
) -> None:
    for name in h5group:
        link = h5group.get(name, getlink=True)
        if isinstance(link, h5py.ExternalLink):
            # Not h5group[name] nor getclass: h5py follows an external link
            # with the options of the file holding it, which fails when that
            # file is open for writing and the linked one cannot be.
            child_source = source.external(link, h5group.file)
            try:
                with child_source.open() as h5child:
                    _add_node(group, name, child_source, h5child)
            except (OSError, KeyError):
                # A link can be broken for any reason; skipping it keeps the
                # rest of the file readable.
                _logger.warning(
                    "Skipping '%s/%s': cannot read '%s::%s'",
                    h5group.name.rstrip("/"),
                    name,
                    child_source.filename,
                    child_source.path,
                    exc_info=True,
                )
            continue

        child_source = source.child(name)
        if h5group.get(name, default=None, getclass=True) is not h5py.Group:
            group.add_node(LiveDataset(name, group, child_source))
            continue

        # Reading the structure through the group which is already open keeps
        # the file open once instead of once per group, which shortens the
        # time a writer of that file is blocked.
        group.add_node(LiveGroup(name, group, child_source, h5group[name]))


def _add_node(
    group: Union[LiveFile, LiveGroup],
    name: str,
    source: _Source,
    h5object: Union[h5py.Group, h5py.Dataset],
) -> None:
    if is_group(h5object):
        group.add_node(LiveGroup(name, group, source, h5object))
    else:
        group.add_node(LiveDataset(name, group, source))
