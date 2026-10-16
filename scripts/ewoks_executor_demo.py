import argparse
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional

import pebble
from AnyQt.QtCore import QEventLoop
from AnyQt.QtCore import Qt
from AnyQt.QtCore import QTimer
from AnyQt.QtGui import QCloseEvent
from AnyQt.QtTest import QTest
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
from ewoksorange.gui.concurrency.future import TaskFuture


class SumTask(
    Task,
    input_names=["a"],
    optional_input_names=["b", "delay", "fail"],
    output_names=["result"],
):
    """Add two numbers with a delay and optional failure. Stops early on request."""

    def run(self) -> None:
        result = self.inputs.a

        if self.inputs.b:
            result += self.inputs.b

        if self.inputs.delay:
            end = time.monotonic() + self.inputs.delay
            while time.monotonic() < end:
                if self.stop_requested:
                    raise RuntimeError("Stopped on request")
                time.sleep(0.05)

        if self.inputs.fail:
            raise RuntimeError(f"Intentional failure after {self.inputs.delay}s")

        self.outputs.result = result

    def _on_stop_requested(self) -> None:
        # `run` polls `stop_requested`.
        pass


_ACTIONS: Dict[str, Callable[[TaskFuture], bool]] = {
    "Cancel (queued only)": TaskFuture.cancel,
    "Request stop": TaskFuture.request_stop,
    "Abort (process only)": TaskFuture.abort,
    "Kill (process only)": TaskFuture.kill,
}


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

        self._log = QTextEdit(readOnly=True)

        self._pending = QListWidget()
        self._pending_items: Dict[int, QListWidgetItem] = {}
        self._futures: Dict[int, TaskFuture] = {}
        self._buttons: Dict[str, QPushButton] = {}
        self._action_buttons: Dict[str, QPushButton] = {}

        self._counter: int = 1
        self._total_tasks_triggered: int = 0
        self._total_tasks_handled: int = 0

        self._executors: Dict[str, EwoksExecutor] = {
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
                pebble.ProcessPool(max_workers=1),
                SubmitPolicy.DROP_IF_BUSY,
            ),
            "P QUEUE": EwoksExecutor(
                pebble.ProcessPool(max_workers=1),
                SubmitPolicy.ALWAYS,
            ),
            "P PARALLEL": EwoksExecutor(
                pebble.ProcessPool(max_workers=4),
                SubmitPolicy.ALWAYS,
            ),
        }

        for name, executor in self._executors.items():
            executor.submitted.connect(partial(self._on_submitted, name))
            executor.started.connect(partial(self._on_started, name))
            executor.ignored.connect(partial(self._on_ignored, name))
            executor.succeeded.connect(partial(self._on_succeeded, name))
            executor.failed.connect(partial(self._on_failed, name))
            executor.cancelled.connect(partial(self._on_cancelled, name))
            executor.stopRequested.connect(partial(self._on_stop_requested, name))
            executor.aborted.connect(partial(self._on_aborted, name))
            executor.killed.connect(partial(self._on_killed, name))
            executor.finished.connect(partial(self._on_finished, name))

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
            button.clicked.connect(partial(self._on_button_clicked, key))
            grid.addWidget(button, i // columns, i % columns)
            self._buttons[key] = button

        layout.addLayout(grid)

        actions = QHBoxLayout()
        actions.addWidget(QLabel("Apply to all queued and running tasks:"))
        for text in _ACTIONS:
            button = QPushButton(text)
            button.clicked.connect(partial(self._on_action_clicked, text))
            actions.addWidget(button)
            self._action_buttons[text] = button
        layout.addLayout(actions)

        body = QHBoxLayout()

        log_box = QVBoxLayout()
        log_box.addWidget(QLabel("Logs"))
        log_box.addWidget(self._log)
        body.addLayout(log_box, 2)

        pending_box = QVBoxLayout()
        pending_box.addWidget(QLabel("Queued and running tasks"))
        pending_box.addWidget(self._pending)
        body.addLayout(pending_box, 1)

        layout.addLayout(body)

    def _append_log(self, message: str) -> None:
        elapsed = time.monotonic() - self._start_time
        log = f"[{elapsed:8.3f}s] {message}"
        print(log)
        self._log.append(log)

    def _on_submitted(self, name: str, future: TaskFuture) -> None:
        self._append_log(f"[{name}] Submitted -> {id(future)}")
        self._futures[id(future)] = future

        item = QListWidgetItem(f"[{name}] {id(future)}")
        self._pending.addItem(item)
        self._pending_items[id(future)] = item

    def _on_started(self, name: str, future: Any) -> None:
        self._append_log(f"[{name}] ▶ Started -> {id(future)}")

    def _on_ignored(self, name: str) -> None:
        self._total_tasks_handled += 1
        self._append_log(f"[{name}] ⚠ Ignored")

    def _on_succeeded(self, name: str, future: Any) -> None:
        result = future.result()
        values = {key: value.value for key, value in result.items()}
        self._append_log(f"[{name}] ✅ {id(future)} -> {values}")

    def _on_failed(self, name: str, future: Any) -> None:
        exc = future.exception()
        self._append_log(f"[{name}] ❌ {id(future)} -> {exc}")

    def _on_cancelled(self, name: str, future: Any) -> None:
        self._append_log(f"[{name}] 🚫 Cancelled -> {id(future)}")

    def _on_stop_requested(self, name: str, future: Any) -> None:
        self._append_log(f"[{name}] ⏹ Stop requested -> {id(future)}")

    def _on_aborted(self, name: str, future: Any) -> None:
        self._append_log(f"[{name}] ⛔ Aborted -> {id(future)}")

    def _on_killed(self, name: str, future: Any) -> None:
        self._append_log(f"[{name}] 💀 Killed -> {id(future)}")

    def _on_finished(self, name: str, future: Any) -> None:
        self._total_tasks_handled += 1
        self._append_log(f"[{name}] ■ Finished -> {id(future)}")
        self._remove_pending(future)

    def _remove_pending(self, future: Any) -> None:
        self._futures.pop(id(future), None)
        item: Optional[QListWidgetItem] = self._pending_items.pop(id(future), None)

        if item is not None:
            self._pending.takeItem(self._pending.row(item))

    def _on_button_clicked(
        self,
        key: str,
        _checked: bool = False,
    ) -> None:
        self._submit_many(self._executors[key])

    def _on_action_clicked(self, text: str, _checked: bool = False) -> None:
        action = _ACTIONS[text]
        futures = [future for future in self._futures.values() if not future.done()]
        accepted = sum(action(future) for future in futures)
        self._append_log(f"{text}: accepted by {accepted}/{len(futures)} tasks")

    def _submit_many(self, executor: EwoksExecutor) -> None:
        for _ in range(self._submit_count):
            executor.submit_task(
                SumTask,
                inputs={
                    "a": self._counter,
                    "b": self._counter,
                    "delay": self._task_duration,
                    "fail": self._fail_after_duration,
                },
            )
            self._total_tasks_triggered += 1
            self._counter += 1

    def closeEvent(self, event: QCloseEvent) -> None:
        for executor in self._executors.values():
            executor.shutdown()

        super().closeEvent(event)

    def is_finished(self, total_tasks: int) -> bool:
        return (
            self._total_tasks_triggered >= total_tasks
            and self._total_tasks_handled >= total_tasks
        )


def run_self_test(window: Window, submit_count: int, timeout: float) -> bool:
    """Click every submit button, then every action button, and wait until all
    submitted tasks finish.

    Used in CI to smoke-test the demo without a real display.
    """

    def on_timeout() -> None:
        print(f"Self-test FAILED: timed out after {timeout}s", flush=True)
        os._exit(1)

    watchdog = threading.Timer(timeout, on_timeout)
    watchdog.daemon = True
    watchdog.start()

    total_tasks_expected = 0
    for button in window._buttons.values():
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        total_tasks_expected += submit_count

    for button in window._action_buttons.values():
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)

    loop = QEventLoop()

    poll_timer = QTimer()

    def check_done() -> None:
        if window.is_finished(total_tasks_expected):
            loop.quit()

    poll_timer.timeout.connect(check_done)
    poll_timer.start(50)

    loop.exec()

    poll_timer.stop()
    watchdog.cancel()

    success = window.is_finished(total_tasks_expected)
    if success:
        print(f"Self-test OK:\n {total_tasks_expected} tasks were handled")
    else:
        print(
            f"Self-test FAILED:"
            f"\n {window._total_tasks_triggered} tasks were triggered "
            f"(expected {total_tasks_expected})"
            f"\n {window._total_tasks_handled} tasks were handled "
            f"(expected {total_tasks_expected})"
        )

    return success


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

    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Click every button, wait for completion and exit (used in CI).",
    )

    parser.add_argument(
        "--self-test-timeout",
        type=float,
        default=60.0,
        help="Maximum time in seconds to wait for the self-test to complete.",
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

    if args.self_test:
        success = run_self_test(window, args.submit_count, args.self_test_timeout)
        window.close()
        sys.exit(0 if success else 1)

    sys.exit(app.exec())
