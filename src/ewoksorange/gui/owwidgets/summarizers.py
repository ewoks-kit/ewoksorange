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
    def summarize_variable(var: Variable) -> PartialSummary:
        """
        Provide a short summary for a Ewoks Variable instance for the Orange UI.

        :param var: The Variable to summarize.
        :return: PartialSummary describing the variable.
        """
        if not var.is_missing():
            return summarize(var.value)

        summary = details = str(var.value)
        return PartialSummary(summary, details)

    @summarize.register(object)
    def summarize_object(value: object) -> PartialSummary:
        """
        Provide a default summary for arbitrary objects for the Orange UI.

        :param value: The object to summarize.
        :return: PartialSummary describing the object's type.
        """
        value = type(object)
        summary = value.__name__
        details = f"{value.__module__}.{value.__name__}: \n{value!r}"
        return PartialSummary(summary, details)

    @summarize.register(type)
    def summarize_type(value: type) -> PartialSummary:
        """
        Provide a default summary for arbitrary types for the Orange UI.

        :param value: The type to summarize.
        :return: PartialSummary describing the type.
        """
        summary = value.__name__
        details = f"{value.__module__}.{value.__name__}"
        return PartialSummary(summary, details)
