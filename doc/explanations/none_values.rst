``None`` on Orange links
========================

.. important::

    If your Ewoks task has an Orange binding, **do not use** ``None`` **as a
    meaningful value for an input passed through a link**. Use a dedicated
    value instead.

    In **Ewoks**, ``None`` is a valid value, while in **Orange** it means
    **"no data"**: if ``None`` is sent through a link, the canvas draws the
    link as a dashed line, and the receiving widget is expected to drop what it
    received earlier on that input.

    **Ewoks-Orange** widgets follow the Orange convention: a ``None`` received
    on a link is considered invalid by
    :func:`~ewoksorange.gui.utils.invalid_data.is_invalid_data` and removes the
    input instead of passing ``None`` to the task.

Technical details
-----------------

Invalid data
^^^^^^^^^^^^

Ewoks-Orange decides what counts as "no data" with
:func:`~ewoksorange.gui.utils.invalid_data.is_invalid_data`. A value is
invalid when it **is** ``None`` (``INVALIDATION_DATA``) or ``MISSING_DATA``.

When an input is invalid, it is removed: the task gets the widget's default
input instead, or the input is missing (a required input makes the task
fail).

What travels through a link
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Between Ewoks-Orange widgets, outputs are sent as
:class:`~ewokscore.variable.Variable` objects, not as raw values. A bare
``None`` only appears on a link in the following cases:

- a **native Orange widget** sends ``None``, for example when its selection is
  cleared;
- an **Ewoks-Orange widget**'s output **value** is ``None`` or ``MISSING_DATA``:
  :meth:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.trigger_downstream`
  checks the variable's value and sends ``None`` instead of the variable;
- an **Ewoks-Orange widget**'s task fails:
  :meth:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.clear_downstream`
  sends ``None`` on all its outputs.

In all these cases the downstream input is removed.

Inputs set by the widget
^^^^^^^^^^^^^^^^^^^^^^^^

Not every task input arrives through an **Orange** link. A widget can also set
inputs itself from the source code, typically from its GUI:

- :meth:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.set_dynamic_input`
  sets an input for the next executions only.
- :meth:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.set_default_input`
  sets an input that is also stored in the widget settings, and therefore
  saved in the ``.ows`` file.

These inputs do not go through a link, so the link display is not involved.
They still follow the same rule though: setting a bare ``None`` with either
method removes the input rather than passing ``None`` to the task.
