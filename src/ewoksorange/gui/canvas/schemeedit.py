import logging
from AnyQt.QtWidgets import QAction
from orangecanvas.document.schemeedit import SchemeEditWidget as _SchemeEditWidget

_logger = logging.getLogger(__name__)


class SchemeEditWidget(_SchemeEditWidget):
    """Class to add the "Trigger" action to the link context menu in the canvas, which allows to trigger again the scan if any in memory."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__linkTriggerAction = QAction(
            self.tr("Trigger"),
            self,
            objectName="link-trigger-action",
            triggered=self.__linkTrigger,
            toolTip=self.tr("Trigger link."),
        )

        linkMenu = self.linkMenu()
        linkMenu.addSeparator()
        linkMenu.addAction(self.__linkTriggerAction)

    def __linkTrigger(self):
        link = self._SchemeEditWidget__contextMenuTarget
        if not link:
            return

        self.removeLink(link)
        self.addLink(link)
