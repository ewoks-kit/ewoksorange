from contextlib import ExitStack
from typing import Optional

from ewokscore import events
from ewokscore.events.contexts import ExecInfoType
from ewokscore.events.contexts import RawExecInfoType


def scheme_ewoks_events(scheme, execinfo: RawExecInfoType = None) -> ExecInfoType:
    scheme_execinfo = getattr(scheme, "ewoks_execinfo", None)
    if scheme_execinfo is not None:
        return scheme_execinfo
    exitstack = ExitStack()
    stack = exitstack.__enter__()
    ctx = events.job_context(execinfo)
    execinfo = stack.enter_context(ctx)
    ctx = events.workflow_context(execinfo, workflow=scheme.title)
    execinfo = stack.enter_context(ctx)
    scheme.ewoks_execinfo = execinfo

    def ewoks_finalize(
        *_qt_signal_args, exception: Optional[BaseException] = None
    ) -> None:
        # When executing a workflow without the Orange canvas GUI, pass the exception
        # on finalization so the job/workflow end events report the failure.
        #
        # TODO: When executing a workflow without the Orange canvas GUI, job and
        # workflow end event will never report node exceptions because they are
        # absorbed by orange.
        if exception is not None and not execinfo.get("exception"):
            execinfo["exception"] = exception
        exitstack.close()

    scheme.ewoks_finalize = ewoks_finalize
    scheme.destroyed.connect(ewoks_finalize)
    return execinfo
