.. _tuto_first_widget_more_hints:

More hints
==========

Widget icons
------------

`qtawesome <https://pypi.org/project/QtAwesome/>`_ is a great library to get access to a large collection of icons. Silx already depends on it. Consider using if you want to have a nice icon for your widget without creating your own.

More usage of the pydantic models
---------------------------------

Retrieving pydantic model fields default values
'''''''''''''''''''''''''''''''''''''''''''''''

Remember that your pydantic models can contain default values.

.. code-block:: python

    class InputModel(BaseInputModel):
        percentiles: tuple[float, float] = (0, 100)
        """percentiles to use for rescaling, must be a tuple of two values (p_min, p_max) with p_min <= p_max"""

    # or 

    class InputModel(BaseInputModel):
        percentiles: tuple[float, float] = description(default=(0, 100), description="percentiles to use for rescaling, must be a tuple of two values (p_min, p_max) with p_min <= p_max")
        

To avoid duplicating this information on the "gui" module you can retrieve those values like:

.. code-block:: python

    default_value = InputModel.model_fields.get("percentiles").default.value
