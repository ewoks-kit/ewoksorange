import importlib.metadata
from enum import Enum

_OrangeVersion = Enum("OrangeVersion", "latest_orange latest_oasys latest_orange_base")

# Order matters: distributions that depend on other distributions in this
# mapping must come first (e.g. OASYS2 depends on orange-canvas-core).
_DISTRIBUTION_TO_VERSION = {
    "oasys2": _OrangeVersion.latest_oasys,
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
