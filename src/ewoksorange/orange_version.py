from enum import Enum
import importlib.metadata

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

# Fix test_cancel_current_task_in_task_executor_queue failures:
if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    import oasys.widgets  # noqa F401
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    import Orange  # noqa F401
