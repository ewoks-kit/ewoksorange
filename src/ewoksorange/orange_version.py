import importlib.metadata
from enum import Enum

_OrangeVersion = Enum("OrangeVersion", "latest_orange oasys_fork latest_orange_base")

_DISTRIBUTION_TO_VERSION = {
    "oasys1": _OrangeVersion.oasys_fork,
    "oasys-canvas-core": _OrangeVersion.oasys_fork,
    "orange3": _OrangeVersion.latest_orange,
    "orange-canvas-core": _OrangeVersion.latest_orange_base,
}

for distribution, version in _DISTRIBUTION_TO_VERSION.items():
    try:
        _ = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        continue
    else:
        ORANGE_VERSION = version
        break
else:
    raise importlib.metadata.PackageNotFoundError(
        "No compatible Orange distributions found."
    )
