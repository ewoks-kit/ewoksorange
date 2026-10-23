import logging

from AnyQt.QtWidgets import QAction
from AnyQt.QtWidgets import QMenu
from orangecanvas.document.schemeedit import SchemeEditWidget as _SchemeEditWidget
from orangecanvas.scheme import SchemeLink

_logger = logging.getLogger(__file__)


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

        runtime_state = link.runtime_state()
        if not link.is_enabled():
            _logger.debug("Won't trigger link %s because it is not active", link)
        elif runtime_state != SchemeLink.State.Active:
            _logger.debug(
                "Won't trigger link %s because runtime state is", runtime_state
            )
        else:
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
