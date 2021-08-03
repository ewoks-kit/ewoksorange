from ewokscore.task import TaskInputError
from ewokscore import TaskWithProgress
from AnyQt.QtCore import QThread
import logging

_logger = logging.getLogger(__name__)


class _TaskExecutor:
    def __init__(self, ewokstaskclass, taskprogress):
        self._inputs = None
        self._output_variables = None
        self._taskprogress = taskprogress
        self._ewokstaskclass = ewokstaskclass
        self._task = None

    @property
    def varinfo(self):
        return self._varinfo

    @property
    def inputs(self):
        return self._inputs

    @property
    def task(self):
        return self._task

    def init(self, varinfo=None, inputs=None):
        self._varinfo = varinfo
        self._inputs = inputs
        self._output_variables = dict()

    @property
    def ewokstaskclass(self):
        return self._ewokstaskclass

    @property
    def output_values(self):
        return {k: v.value for k, v in self._output_variables.items()}

    @property
    def output_variables(self):
        return self._output_variables

    def create_task(self):
        args = {"inputs": self.inputs, "varinfo": self.varinfo}
        if issubclass(self.ewokstaskclass, TaskWithProgress):
            args["progress"] = self._taskprogress
        self._task = self.ewokstaskclass(**args)
        return self._task

    def run(self):
        if self.task is None:
            raise ValueError("Task must be created first")
        self.task.execute()
        self._output_variables = self.task.output_variables


class _ProcessingThread(QThread, _TaskExecutor):
    """
    Run a task on a QThread
    """

    def run(self):
        try:
            self.create_task()
        except TaskInputError as e:
            _logger.warning(e)
            return
        if not self.task.is_ready_to_execute:
            return
        try:
            _TaskExecutor.run(self)
        except TaskInputError as e:
            _logger.warning(e)
            return
        except Exception:
            raise
