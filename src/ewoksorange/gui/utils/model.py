from typing import Any
from typing import Dict
from typing import Iterator
from typing import Tuple
from typing import Type

from pydantic import BaseModel
from pydantic_core import PydanticUndefined


def get_model_default_values(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    :return: Dict of input name -> value or missing marker.
    """
    field_with_values = filter(
        lambda pair: pair[1] is not PydanticUndefined,
        _get_default_field_factory(model=model),
    )
    return dict(field_with_values)


def _get_default_field_factory(model) -> Iterator[Tuple[str, Any]]:
    for field_name, field in model.model_fields.items():
        yield field_name, field.default
