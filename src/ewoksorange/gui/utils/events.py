import weakref
from contextlib import ExitStack
from typing import Any
from typing import Optional

from ewokscore import events
from ewokscore.events.contexts import ExecInfoType
from ewokscore.events.contexts import RawExecInfoType

# The ewoks job id of a scheme is shared by all tasks executed from that scheme.
_SCHEME_BY_JOB_ID = weakref.WeakValueDictionary()


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
    job_id = execinfo["job_id"] if execinfo else None
    if job_id is not None:
        _SCHEME_BY_JOB_ID[job_id] = scheme
    scheme_ref = weakref.ref(scheme)  # no reference cycle through the closure

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
        registered = _SCHEME_BY_JOB_ID.get(job_id) if job_id is not None else None
        if registered is not None and registered is scheme_ref():
            del _SCHEME_BY_JOB_ID[job_id]
        exitstack.close()

    scheme.ewoks_finalize = ewoks_finalize
    scheme.destroyed.connect(ewoks_finalize)
    return execinfo


def scheme_from_job_id(job_id: Optional[str]) -> Optional[Any]:
    """The Orange scheme from which tasks with this ewoks job id are executed.

    :param job_id: The ewoks job id of a task (`Task.job_id`).
    :return: The `WidgetsScheme` or `None` when the task was not executed from
             an Orange scheme in this process.
    """
    if job_id is None:
        return None
    return _SCHEME_BY_JOB_ID.get(job_id)
