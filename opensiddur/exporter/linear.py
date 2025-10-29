""" Singleton class to hold data from linear processing.

Linear processing treats the entire hierarchy as a single pass,
so the data are the same independent of depth.
"""
from typing import Annotated, Any, Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from opensiddur.exporter.cache import XMLCache


class Setting(BaseModel):
    fs_type: str
    name: str
    value: Any


class LinearData(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True)
    
    # parsed XML cache
    xml_cache: XMLCache = Field(default_factory=XMLCache)
    # dictionary linking the starting point of the settings to changes at that point.
    settings: list[tuple[str, Setting]] = Field(default_factory=list)
    # project priority for URN resolution of texts
    project_priority: list[str] = Field(default_factory=list)
    # project priority for URN resolution of instructions
    instruction_priority: list[str] = Field(default_factory=list)
    # projects from which to include annotations (not a priority list)
    annotation_projects: list[str] = Field(default_factory=list)
    # processing context includes processor-specific data. Because there is recursion, it acts as a stack.
    processing_context: list[dict[str, Any]] = Field(default_factory=list)

_linear_data = LinearData()

def reset_linear_data():
    global _linear_data
    _linear_data = LinearData()

def get_linear_data() -> LinearData:
    global _linear_data
    return _linear_data