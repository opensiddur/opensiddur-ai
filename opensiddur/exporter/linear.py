""" Singleton class to hold data from linear processing.

Linear processing treats the entire hierarchy as a single pass,
so the data are the same independent of depth.
"""
from typing import Any, TypedDict

from pydantic import BaseModel


class Setting(BaseModel):
    fs_type: str
    name: str
    value: Any


class LinearData(TypedDict):
    # dictionary linking the starting point of the settings to changes at that point.
    settings: list[tuple[str, Setting]]

_linear_data = LinearData()

def reset_linear_data():
    global _linear_data
    _linear_data = LinearData()

def get_linear_data() -> LinearData:
    global _linear_data
    return _linear_data