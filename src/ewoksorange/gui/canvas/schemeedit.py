import logging
from AnyQt.QtWidgets import QAction, QMenu
from orangecanvas.document.schemeedit import SchemeEditWidget as _SchemeEditWidget
from orangecanvas.scheme import SchemeLink

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
        self.__link = None  # type: Optional[SchemeLink]
        # Active link in the context menu.

    def __linkTrigger(self):
        link = self.__link
        if not link:
            return

        self.removeLink(link)
        self.addLink(link)

    def contextMenuForLink(self, link: SchemeLink) -> QMenu:
        """
        Return a `QMenu` for a context click on the connection represented
        by `link`.
        """
        menu = super().contextMenuForLink(link)
        self.__link = link
        return menu
