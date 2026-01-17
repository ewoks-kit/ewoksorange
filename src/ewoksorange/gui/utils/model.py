from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic_core import PydanticUndefined


def _get_model_default_values(model: type[BaseModel]) -> dict[str, Any]:
    """
    Docstring for _get_model_default_values

    :return: Dict of input name -> value or missing marker.
    """
    field_with_values = filter(
        lambda pair: pair[1] is not PydanticUndefined,
        _get_default_field_factory(model=model),
    )
    return dict(field_with_values)


def _get_default_field_factory(model):
    for field_name, field in model.model_fields.items():
        yield field_name, field.default
