from contextlib import ExitStack

# import weakref
from ewokscore import events
from ewokscore.events.contexts import ExecInfoType
from ewokscore.events.contexts import ExecInfoType0


def scheme_ewoks_events(scheme, execinfo: ExecInfoType0 = None) -> ExecInfoType:
    scheme_execinfo = getattr(scheme, "ewoks_execinfo", None)
    if scheme_execinfo is not None:
        return scheme_execinfo
    exitstack = ExitStack()
    stack = exitstack.__enter__()
    ctx = events.job_context(execinfo)
    execinfo = stack.enter_context(ctx)
    ctx = events.workflow_context(execinfo)
    execinfo = stack.enter_context(ctx)
    if scheme.title:
        execinfo["workflow_id"] = scheme.title
    scheme.ewoks_execinfo = execinfo
    # TODO: find a way to execute the exit
    # weakref.finalize(scheme, exitstack.__exit__)
    return execinfo
