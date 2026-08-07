"""
Metaclass and class preparation utilities for owwidgets package.
"""

import inspect
import multiprocessing
import multiprocessing.context
from abc import ABCMeta
from typing import Any
from typing import Optional
from typing import Union

from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from orangewidget.settings import Setting
    from orangewidget.widget import WidgetMetaClass
else:
    from orangewidget.settings import Setting

    if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        from Orange.widgets.widget import WidgetMetaClass
    else:
        from orangewidget.widget import OWBaseWidget

        WidgetMetaClass = type(OWBaseWidget)

from ..concurrency.executor import Concurrency
from ..concurrency.executor import SubmitPolicy
from ..orange_utils import _signals

_NOT_PROVIDED = object()


class OWEwoksWidgetMetaClass(ABCMeta, WidgetMetaClass):
    """
    Metaclass used to prepare widget classes with Ewoks bindings.
    """

    def __new__(
        metacls,
        name,
        bases,
        attrs,
        ewokstaskclass=None,
        concurrency=_NOT_PROVIDED,
        max_workers=_NOT_PROVIDED,
        submit_policy=_NOT_PROVIDED,
        mp_context=_NOT_PROVIDED,
        **kw,
    ):
        """
        Create a new widget class; if `ewokstaskclass` is provided prepare the class.

        Execution arguments that are not provided are inherited from the base classes.

        :param name: New class name.
        :param bases: Base classes.
        :param attrs: Attribute dict for the class.
        :param ewokstaskclass: Optional Ewoks Task class to attach.
        :param concurrency: Optional task execution backend (see
                            :attr:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget._CONCURRENCY`).
        :param max_workers: Optional maximum number of task workers (see
                            :attr:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget._MAX_WORKERS`).
        :param submit_policy: Optional task submission policy (see
                              :attr:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget._SUBMIT_POLICY`).
        :param mp_context: Optional multiprocessing context (see
                           :attr:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget._MP_CONTEXT`).
        :return: Newly created class type.
        """
        if ewokstaskclass:
            _prepare_OWEwoksWidgetclass(attrs, ewokstaskclass)
        if concurrency is not _NOT_PROVIDED:
            attrs["_CONCURRENCY"] = _parse_concurrency(concurrency)
        if max_workers is not _NOT_PROVIDED:
            attrs["_MAX_WORKERS"] = _parse_max_workers(max_workers)
        if submit_policy is not _NOT_PROVIDED:
            attrs["_SUBMIT_POLICY"] = _parse_submit_policy(submit_policy)
        if mp_context is not _NOT_PROVIDED:
            attrs["_MP_CONTEXT"] = _parse_mp_context(mp_context)
        return super().__new__(metacls, name, bases, attrs, **kw)


def _parse_concurrency(concurrency: Union[Concurrency, str]) -> Concurrency:
    """
    Validate the `concurrency` class argument.

    :param concurrency: A :class:`Concurrency` or its (case-insensitive) name.
    :raises ValueError: When the name is unknown.
    :return: The corresponding :class:`Concurrency`.
    """
    if isinstance(concurrency, Concurrency):
        return concurrency
    if isinstance(concurrency, str):
        try:
            return Concurrency[concurrency.upper()]
        except KeyError:
            pass
    names = ", ".join(repr(value.name.lower()) for value in Concurrency)
    raise ValueError(
        f"'concurrency' must be a Concurrency or one of {names}: {concurrency!r}"
    )


def _parse_max_workers(max_workers: Optional[int]) -> Optional[int]:
    """
    Validate the `max_workers` class argument.

    :param max_workers: `None` or a positive integer.
    :raises ValueError: When not a positive integer.
    :return: The validated value.
    """
    if max_workers is None:
        return None
    if not isinstance(max_workers, int) or isinstance(max_workers, bool):
        raise ValueError(f"'max_workers' must be None or an integer: {max_workers!r}")
    if max_workers < 1:
        raise ValueError(
            f"'max_workers' must be None or a positive integer: {max_workers!r}"
        )
    return max_workers


def _parse_submit_policy(submit_policy: Union[SubmitPolicy, str]) -> SubmitPolicy:
    """
    Validate the `submit_policy` class argument.

    :param submit_policy: A :class:`SubmitPolicy` or its (case-insensitive) name.
    :raises ValueError: When the name is unknown.
    :return: The corresponding :class:`SubmitPolicy`.
    """
    if isinstance(submit_policy, SubmitPolicy):
        return submit_policy
    if isinstance(submit_policy, str):
        try:
            return SubmitPolicy[submit_policy.upper()]
        except KeyError:
            pass
    names = ", ".join(repr(policy.name.lower()) for policy in SubmitPolicy)
    raise ValueError(
        f"'submit_policy' must be a SubmitPolicy or one of {names}: {submit_policy!r}"
    )


def _parse_mp_context(
    mp_context: Union[None, str, multiprocessing.context.BaseContext],
) -> Optional[multiprocessing.context.BaseContext]:
    """
    Validate the `mp_context` class argument.

    :param mp_context: `None` for the platform default, a `multiprocessing`
                       context or the name of a start method supported on this
                       platform (for example `"spawn"`).
    :raises ValueError: When the start method is not available.
    :return: The corresponding `multiprocessing` context or `None`.
    """
    if mp_context is None or isinstance(
        mp_context, multiprocessing.context.BaseContext
    ):
        return mp_context
    available = multiprocessing.get_all_start_methods()
    if not isinstance(mp_context, str) or mp_context not in available:
        names = ", ".join(repr(name) for name in available)
        raise ValueError(
            f"'mp_context' must be None, a multiprocessing context or one of {names} on this platform: {mp_context!r}"
        )
    return multiprocessing.get_context(mp_context)


# Ensure compatibility between old orange widget and new
# orangewidget.widget.WidgetMetaClass. This was before the split of the two
# projects. Parameter name "openclass" is undefined in the old version.
ow_build_opts = dict()
if "openclass" in inspect.signature(WidgetMetaClass).parameters:
    ow_build_opts["openclass"] = True


def _prepare_OWEwoksWidgetclass(namespace: dict, ewokstaskclass: Any) -> None:
    """
    Attach Ewoks task class and default settings to a widget class namespace.
    This needs to be called before signal and setting parsing.

    :param namespace: Class attribute dictionary to modify.
    :param ewokstaskclass: The Ewoks Task class to attach (used for input/output introspection).
    """

    # Add the Ewoks class as an attribute to the Orange widget class
    namespace["ewokstaskclass"] = ewokstaskclass
    _ = namespace.setdefault("name", ewokstaskclass.__name__)

    # Make sure the values above are always the default setting values:
    # https://orange3.readthedocs.io/projects/orange-development/en/latest/tutorial-settings.html
    # schema_only=False: when a widget is removed, its settings are stored to be used
    #                    as defaults for future instances of this widget.
    # schema_only=True: setting defaults should not change. Future instances of this widget
    #                   have the default settings hard-coded in this function.
    schema_only = True

    # Add the settings as widget class attributes
    namespace["_ewoks_default_inputs"] = Setting(dict(), schema_only=schema_only)
    namespace["_ewoks_varinfo"] = Setting(dict(), schema_only=schema_only)
    namespace["_ewoks_execinfo"] = Setting(dict(), schema_only=schema_only)
    namespace["_ewoks_task_options"] = Setting(dict(), schema_only=schema_only)

    # Hide Ewoks task variables from Orange: do not create Orange signals
    hidden_inputs = namespace.setdefault("_ewoks_inputs_to_hide_from_orange", tuple())
    hidden_outputs = namespace.setdefault("_ewoks_outputs_to_hide_from_orange", tuple())

    # Deprecated:
    namespace["default_inputs"] = Setting(dict(), schema_only=schema_only)

    # Add missing inputs and outputs as widget class attributes
    _signals.validate_signals(namespace, "inputs", name_to_ignore=hidden_inputs)
    _signals.validate_signals(namespace, "outputs", name_to_ignore=hidden_outputs)
