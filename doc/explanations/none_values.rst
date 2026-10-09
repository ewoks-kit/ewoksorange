``None`` on Orange links
========================

In **Ewoks**, ``None`` is a valid value while in **Orange** it means **"no data"**. If ``None`` is sent though a link, the canvas draws it as a dashed line, and the
receiving widget is expected to drop what it received earlier on that input.

**Ewoks-Orange** widgets follow the Orange convention for what goes through links.

Invalid data
------------

Ewoks-Orange decides what counts as "no data" with
:func:`~ewoksorange.gui.utils.invalid_data.is_invalid_data`. A value is
invalid when it **is** ``None`` (``INVALIDATION_DATA``) or ``MISSING_DATA``.

The check is on the object itself: a :class:`~ewokscore.variable.Variable`
whose value is ``None`` is **not** invalid. Only a bare ``None`` is.

Where task inputs come from
---------------------------

Not every task input arrives through an **Orange** link. A widget can also set inputs
itself from the source code, typically from its GUI:

- :meth:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.set_dynamic_input`
  sets an input for the next executions only.
- :meth:`~ewoksorange.gui.owwidgets.base.OWEwoksBaseWidget.set_default_input`
  sets an input that is also stored in the widget settings, and therefore
  saved in the ``.ows`` file.

When storing an input by those two last methods, we fall back to the ewokscore default mechanism. And we don't have to care about coherence with **Orange** links, because the input is set directly in the task.

What travels through a link
---------------------------

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

In all these cases the downstream input is removed, as described above.

Recommendation
--------------

Do not rely on ``None`` reaching the next task through an **Orange** link. If ``None``
is a meaningful value for your task, use a dedicated value instead.
