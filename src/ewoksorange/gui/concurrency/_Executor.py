class CancellableExecutor:
    def _cancel_future(self, future) -> bool:
        """Cancel a pending future"""
        raise NotImplementedError("Base class")


class AbortableExecutor:
    def _abort_future(self, future) -> bool:
        """Abort a running future"""
        raise NotImplementedError("Base class")
