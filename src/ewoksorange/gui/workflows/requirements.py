import importlib.metadata
import logging
import threading
from typing import Dict
from typing import Optional

from ewokscore import requirements
from ewokscore.graph import TaskGraph

logger = logging.getLogger(__name__)

_prefetch_thread: Optional[threading.Thread] = None


def prefetch_requirements() -> None:
    """Generate the requirements in a background thread. Saving a workflow then
    only waits when the generation has not finished yet."""
    global _prefetch_thread
    if _prefetch_thread is not None:
        return
    _prefetch_thread = threading.Thread(
        target=_prefetch, name="ewoks-requirements", daemon=True
    )
    _prefetch_thread.start()


def generate_requirements() -> dict:
    _wait_for_prefetch()
    return requirements.generate_requirements(bootstrap=_bootstrap())


def add_requirements(graph: TaskGraph) -> None:
    _wait_for_prefetch()
    requirements.add_requirements(graph, bootstrap=_bootstrap())


def _bootstrap() -> Dict[str, str]:
    return {"ewoksorange": importlib.metadata.version("ewoksorange")}


def _prefetch() -> None:
    try:
        requirements.generate_requirements(bootstrap=_bootstrap())
    except Exception:
        # Not cached: generating again when saving reports the error
        logger.debug("Failed to generate the workflow requirements", exc_info=True)


def _wait_for_prefetch() -> None:
    if _prefetch_thread is not None:
        _prefetch_thread.join()
