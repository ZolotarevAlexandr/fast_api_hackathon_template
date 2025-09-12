__all__ = ['BaseSchema']

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)
