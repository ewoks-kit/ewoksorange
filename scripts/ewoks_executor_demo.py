import argparse
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any
from typing import Dict
from typing import Optional

from AnyQt.QtGui import QCloseEvent
from AnyQt.QtWidgets import QApplication
from AnyQt.QtWidgets import QGridLayout
from AnyQt.QtWidgets import QHBoxLayout
from AnyQt.QtWidgets import QLabel
from AnyQt.QtWidgets import QListWidget
from AnyQt.QtWidgets import QListWidgetItem
from AnyQt.QtWidgets import QPushButton
from AnyQt.QtWidgets import QTextEdit
from AnyQt.QtWidgets import QVBoxLayout
from AnyQt.QtWidgets import QWidget
from ewokscore.task import Task

from ewoksorange.gui.concurrency.executor import EwoksExecutor
from ewoksorange.gui.concurrency.executor import SubmitPolicy


class SumTask(
    Task,
    input_names=["a"],
    optional_input_names=["b", "delay", "fail"],
    output_names=["result"],
):
    """Add two numbers with a delay and optional failure."""

    def run(self) -> None:
        result = self.inputs.a

        if self.inputs.b:
            result += self.inputs.b

        if self.inputs.delay:
            time.sleep(self.inputs.delay)

        if self.inputs.fail:
            raise RuntimeError(f"Intentional failure after {self.inputs.delay}s")

        self.outputs.result = result


class Window(QWidget):
    def __init__(
        self,
        submit_count: int = 5,
        task_duration: float = 2.0,
        fail_after_duration: bool = False,
        **kw: Any,
    ) -> None:
        super().__init__(**kw)

        self._submit_count = submit_count
        self._task_duration = task_duration
        self._fail_after_duration = fail_after_duration
        self._start_time = time.monotonic()

        self.setWindowTitle("EwoksExecutor Demo")

        self.log = QTextEdit(readOnly=True)

        self.pending = QListWidget()
        self.pending_items: Dict[int, QListWidgetItem] = {}

        self.executors: Dict[str, EwoksExecutor] = {
            # Synchronous
            "S DROP": EwoksExecutor(
                None,
                SubmitPolicy.DROP_IF_BUSY,
            ),
            "S QUEUE": EwoksExecutor(
                None,
                SubmitPolicy.ALWAYS,
            ),
            "S PARALLEL": EwoksExecutor(
                None,
                SubmitPolicy.ALWAYS,
            ),
            # Threads
            "T DROP": EwoksExecutor(
                ThreadPoolExecutor(max_workers=1),
                SubmitPolicy.DROP_IF_BUSY,
            ),
            "T QUEUE": EwoksExecutor(
                ThreadPoolExecutor(max_workers=1),
                SubmitPolicy.ALWAYS,
            ),
            "T PARALLEL": EwoksExecutor(
                ThreadPoolExecutor(max_workers=4),
                SubmitPolicy.ALWAYS,
            ),
            # Processes
            "P DROP": EwoksExecutor(
                ProcessPoolExecutor(max_workers=1),
                SubmitPolicy.DROP_IF_BUSY,
            ),
            "P QUEUE": EwoksExecutor(
                ProcessPoolExecutor(max_workers=1),
                SubmitPolicy.ALWAYS,
            ),
            "P PARALLEL": EwoksExecutor(
                ProcessPoolExecutor(max_workers=4),
                SubmitPolicy.ALWAYS,
            ),
        }

        for name, executor in self.executors.items():
            executor.submitted.connect(partial(self.on_submitted, name))
            executor.started.connect(partial(self.on_started, name))
            executor.ignored.connect(partial(self.on_ignored, name))
            executor.succeeded.connect(partial(self.on_succeeded, name))
            executor.failed.connect(partial(self.on_failed, name))
            executor.aborted.connect(partial(self.on_aborted, name))
            executor.finished.connect(partial(self.on_finished, name))

        layout = QVBoxLayout(self)

        grid = QGridLayout()

        buttons = [
            # Drop
            (f"Submit x{self._submit_count} (Sync Drop)", "S DROP"),
            (f"Submit x{self._submit_count} (Thread Drop)", "T DROP"),
            (f"Submit x{self._submit_count} (Process Drop)", "P DROP"),
            # Queue
            (f"Submit x{self._submit_count} (Sync Queue)", "S QUEUE"),
            (f"Submit x{self._submit_count} (Thread Queue)", "T QUEUE"),
            (f"Submit x{self._submit_count} (Process Queue)", "P QUEUE"),
            # Parallel
            (f"Submit x{self._submit_count} (Sync Parallel)", "S PARALLEL"),
            (f"Submit x{self._submit_count} (Thread Parallel)", "T PARALLEL"),
            (f"Submit x{self._submit_count} (Process Parallel)", "P PARALLEL"),
        ]

        columns = 3

        for i, (text, key) in enumerate(buttons):
            button = QPushButton(text)
            button.clicked.connect(partial(self.on_button_clicked, key))
            grid.addWidget(button, i // columns, i % columns)

        layout.addLayout(grid)

        body = QHBoxLayout()

        log_box = QVBoxLayout()
        log_box.addWidget(QLabel("Logs"))
        log_box.addWidget(self.log)
        body.addLayout(log_box, 2)

        pending_box = QVBoxLayout()
        pending_box.addWidget(QLabel("Pending jobs"))
        pending_box.addWidget(self.pending)
        body.addLayout(pending_box, 1)

        layout.addLayout(body)

        self.counter: int = 1

    def append_log(self, message: str) -> None:
        elapsed = time.monotonic() - self._start_time
        log = f"[{elapsed:8.3f}s] {message}"
        print(log)
        self.log.append(log)

    def on_submitted(self, name: str, future: Any) -> None:
        self.append_log(f"[{name}] Submitted -> {id(future)}")

        item = QListWidgetItem(f"[{name}] {id(future)}")
        self.pending.addItem(item)
        self.pending_items[id(future)] = item

    def on_started(self, name: str, future: Any) -> None:
        self.append_log(f"[{name}] ▶ Started -> {id(future)}")

    def on_ignored(self, name: str) -> None:
        self.append_log(f"[{name}] ⚠ Ignored")

    def on_succeeded(
        self,
        name: str,
        future: Any,
        result: Dict[str, Any],
    ) -> None:
        values = {key: value.value for key, value in result.items()}
        self.append_log(f"[{name}] ✅ {id(future)} -> {values}")

    def on_failed(
        self,
        name: str,
        future: Any,
        exc: BaseException,
    ) -> None:
        self.append_log(f"[{name}] ❌ {id(future)} -> {exc}")

    def on_aborted(self, name: str, future: Any) -> None:
        self.append_log(f"[{name}] ⏹ Aborted -> {id(future)}")

    def on_finished(self, name: str, future: Any) -> None:
        self.append_log(f"[{name}] ■ Finished -> {id(future)}")
        self.remove_pending(future)

    def remove_pending(self, future: Any) -> None:
        item: Optional[QListWidgetItem] = self.pending_items.pop(id(future), None)

        if item is not None:
            self.pending.takeItem(self.pending.row(item))

    def on_button_clicked(
        self,
        key: str,
        _checked: bool = False,
    ) -> None:
        self.submit_many(self.executors[key])

    def submit_many(self, executor: EwoksExecutor) -> None:
        for _ in range(self._submit_count):
            executor.submit_task(
                SumTask,
                inputs={
                    "a": self.counter,
                    "b": self.counter,
                    "delay": self._task_duration,
                    "fail": self._fail_after_duration,
                },
            )
            self.counter += 1

    def closeEvent(self, event: QCloseEvent) -> None:
        for executor in self.executors.values():
            executor.shutdown()

        super().closeEvent(event)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EwoksExecutor concurrency demo")

    parser.add_argument(
        "--submit-count",
        type=int,
        default=(os.cpu_count() or 1) + 1,
        help="Number of tasks submitted per button click.",
    )

    parser.add_argument(
        "--task-duration",
        type=float,
        default=2.0,
        help="Task execution duration in seconds.",
    )

    parser.add_argument(
        "--fail-after-duration",
        action="store_true",
        help="Fail tasks after sleeping for task-duration.",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging level.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
    )

    app = QApplication(sys.argv)

    window = Window(
        submit_count=args.submit_count,
        task_duration=args.task_duration,
        fail_after_duration=args.fail_after_duration,
    )

    window.resize(950, 550)
    window.show()

    sys.exit(app.exec())
