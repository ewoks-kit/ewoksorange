from typing import Any
from typing import Dict
from typing import Iterator
from typing import Tuple
from typing import Type

from pydantic import BaseModel
from pydantic_core import PydanticUndefined


def get_model_default_values(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    :return: Dict of input name -> default value, for the fields with a default value.
    """
    return dict(_iter_default_values(model))


def _iter_default_values(model: Type[BaseModel]) -> Iterator[Tuple[str, Any]]:
    for field_name, field in model.model_fields.items():
        if field.default is PydanticUndefined:
            # Required field, or field with a default factory.
            continue
        yield field_name, field.get_default()
