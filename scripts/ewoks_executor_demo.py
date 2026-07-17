import logging
import sys
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from functools import partial

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
from ewokscore.tests.examples.tasks.sumtask import SumTask

from ewoksorange.gui.concurrency.executor import EwoksExecutor
from ewoksorange.gui.concurrency.executor import SubmitPolicy


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EwoksExecutor Demo")

        self.log = QTextEdit(readOnly=True)

        self.pending = QListWidget()
        self.pending_items = {}

        self.executors = {
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
            executor.ignored.connect(partial(self.on_ignored, name))
            executor.succeeded.connect(partial(self.on_succeeded, name))
            executor.failed.connect(partial(self.on_failed, name))

        layout = QVBoxLayout(self)
        grid = QGridLayout()

        buttons = [
            ("Submit x5 (Thread Drop)", "T DROP"),
            ("Submit x5 (Process Drop)", "P DROP"),
            ("Submit x5 (Thread Queue)", "T QUEUE"),
            ("Submit x5 (Process Queue)", "P QUEUE"),
            ("Submit x5 (Thread Parallel)", "T PARALLEL"),
            ("Submit x5 (Process Parallel)", "P PARALLEL"),
        ]

        for i, (text, key) in enumerate(buttons):
            button = QPushButton(text)
            button.clicked.connect(partial(self.on_button_clicked, key))
            grid.addWidget(button, i // 2, i % 2)

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

        self.counter = 1

    def on_submitted(self, name, future):
        if future is None:
            self.log.append(f"[{name}] Submitted -> None")
        else:
            self.log.append(f"[{name}] Submitted -> {id(future)}")
            item = QListWidgetItem(f"[{name}] {id(future)}")
            self.pending.addItem(item)
            self.pending_items[id(future)] = item

    def on_ignored(self, name):
        self.log.append(f"[{name}] ⚠ Ignored")

    def on_succeeded(self, name, future, result):
        values = {k: v.value for k, v in result.items()}
        self.log.append(f"[{name}] ✅ {id(future)} -> {values}")
        self.remove_pending(future)

    def on_failed(self, name, future, exc):
        self.log.append(f"[{name}] ❌ {id(future)} -> {exc}")
        self.remove_pending(future)

    def remove_pending(self, future):
        item = self.pending_items.pop(id(future), None)
        if item is not None:
            self.pending.takeItem(self.pending.row(item))

    def on_button_clicked(self, key, _checked=False):
        self.submit_many(self.executors[key])

    def submit_many(self, executor):
        for _ in range(5):
            executor.submit_task(
                SumTask, inputs={"a": self.counter, "b": self.counter, "delay": 2}
            )
            self.counter += 1

    def closeEvent(self, event):
        for executor in self.executors.values():
            executor.shutdown()
        super().closeEvent(event)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)

    window = Window()
    window.resize(900, 500)
    window.show()

    sys.exit(app.exec())
