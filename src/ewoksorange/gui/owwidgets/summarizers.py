"""
Summarizers for Orange signal display integration.
"""

from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    summarize = None
    PartialSummary = None
else:
    from orangewidget.utils.signals import PartialSummary
    from orangewidget.utils.signals import summarize

from ewokscore.variable import Variable

if summarize is not None:

    @summarize.register(Variable)
    def summarize_variable(var: Variable):
        """
        Provide a short summary for Ewoks Variable instances for Orange UI.

        :param var: The Variable to summarize.
        :return: PartialSummary describing the variable.
        """
        if var.is_missing():
            dtype = var.value
        else:
            dtype = type(var.value).__name__
        desc = f"ewoks variable ({dtype})"
        return PartialSummary(desc, desc)

    @summarize.register(object)
    def summarize_object(value: object):
        """
        Provide a default summary for arbitrary objects.

        :param value: The object to summarize.
        :return: PartialSummary describing the object's type.
        """
        return PartialSummary(str(type(value)), str(type(value)))
