import os

from ewokscore import Task


class SaveWorkflow(Task, input_names=["filename"], output_names=["filename"]):
    """Save the Orange workflow from which this task is executed, with the current
    settings of all its widgets, to an `.ows` file.

    The workflow is retrieved from the Orange canvas by the ewoks job id of the
    task, which is shared by all tasks executed from the same Orange scheme. The
    task must therefore be executed from an Orange canvas, in the canvas process.

    Inputs:

    - `filename`: destination `.ows` file. Overwritten when it exists.

    Outputs:

    - `filename`: absolute path of the saved file.
    """

    def run(self):
        # Imported here: the task module must be importable without Qt.
        from ..gui.qt_utils.gui_thread import call_in_gui_thread
        from ..gui.utils.events import scheme_from_job_id
        from ..gui.workflows.owscheme import scheme_to_ows_bytes

        scheme = scheme_from_job_id(self.job_id)
        if scheme is None:
            raise RuntimeError(
                "No Orange workflow to save: this task must be executed from the Orange canvas"
            )

        filename = os.path.abspath(self.inputs.filename)
        # Widget settings can only be accessed from the Qt GUI thread
        content = call_in_gui_thread(lambda: scheme_to_ows_bytes(scheme, filename))

        dirname = os.path.dirname(filename)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(filename, "wb") as f:
            f.write(content)

        self.outputs.filename = filename
