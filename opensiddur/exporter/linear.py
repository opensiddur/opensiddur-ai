""" Singleton class to hold data from linear processing.

Linear processing treats the entire hierarchy as a single pass,
so the data are the same independent of depth.
"""
from enum import StrEnum
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

# Literal values allowed in exporter settings YAML ``declarations`` (null → Undefined).
DeclarationFeatureValue: TypeAlias = int | float | bool | str | None

from opensiddur.exporter.cache import XMLCache


class UndefinedType:
    """Sentinel for undefined / any-value feature semantics."""

    _instance: "UndefinedType | None" = None

    def __new__(cls) -> "UndefinedType":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "Undefined"


Undefined = UndefinedType()


class NumericValue(BaseModel):
    """Parsed tei:numeric value, optionally with inclusive upper bound (@max)."""

    value: int
    max_value: int | None = None


class ConditionalSettingEntry(BaseModel):
    declare_id: str
    fs_type: str
    feature_name: str
    value: Any
    source: Literal["init", "declared", "derived"]
    contributors: set[str] = Field(default_factory=set)


class ParallelColumnOrder(StrEnum):
    PRIMARY_FIRST = "primary_first"
    PRIMARY_LAST = "primary_last"


class LinearData(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True)

    # parsed XML cache
    xml_cache: XMLCache = Field(default_factory=XMLCache)
    # scoped conditional setting stack (init, declared, derived entries)
    conditional_settings: list[ConditionalSettingEntry] = Field(default_factory=list)
    # contributor declare_id -> stack indices of derived entries that depend on it
    derived_dependency_index: dict[str, set[int]] = Field(default_factory=dict)
    # project priority for URN resolution of texts
    project_priority: list[str] = Field(default_factory=list)
    # project priority for URN resolution of instructions
    instruction_priority: list[str] = Field(default_factory=list)
    # projects from which to include annotations (not a priority list)
    annotation_projects: list[str] = Field(default_factory=list)
    # processing context includes processor-specific data. Because there is recursion, it acts as a stack.
    processing_context: list[dict[str, Any]] = Field(default_factory=list)
    # projects to search for parallel text content (in priority order)
    parallel_projects: list[str] = Field(default_factory=list)
    # column order for parallel text display
    parallel_column_order: ParallelColumnOrder = Field(default=ParallelColumnOrder.PRIMARY_FIRST)

_linear_data = LinearData()

def reset_linear_data():
    global _linear_data
    _linear_data = LinearData()

def get_linear_data() -> LinearData:
    global _linear_data
    return _linear_data
