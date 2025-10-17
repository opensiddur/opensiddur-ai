""" Singleton class to hold data from linear processing.

Linear processing treats the entire hierarchy as a single pass,
so the data are the same independent of depth.
"""
from typing import Annotated, Any, Optional, TypedDict

from pydantic import BaseModel, Field

from opensiddur.exporter.cache import XMLCache


class Setting(BaseModel):
    fs_type: str
    name: str
    value: Any


class LinearData(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    # parsed XML cache
    xml_cache: Optional[XMLCache] = Annotated[..., Field(default_factory=XMLCache)]
    # dictionary linking the starting point of the settings to changes at that point.
    settings: list[tuple[str, Setting]] = Annotated[..., Field(default_factory=list)]

_linear_data = LinearData()

def reset_linear_data():
    global _linear_data
    _linear_data = LinearData()

def get_linear_data() -> LinearData:
    global _linear_data
    return _linear_data